import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.figure_factory as ff
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO

st.set_page_config(
    page_title="Data Exploration",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply styles
st.markdown(
    """
    <style>
    :root {
        font-size: 11px !important;
    }
    section[data-testid="stSidebar"][aria-expanded="true"] {
        width: 180px !important;
        min-width: 180px !important;
    }
    section[data-testid="stSidebar"][aria-expanded="false"] {
        width: 0 !important;
        min-width: 0 !important;
        margin-left: 0 !important;
    }
    html, body, .stApp, * {font-size:11px !important;}
    .stMarkdown p, .stMarkdown span, .stMarkdown li {font-size:11px !important;}
    .stButton button {font-size:10px !important; padding:0.1rem 0.3rem !important;}
    .stTextInput input, .stNumberInput input {font-size:10px !important; padding:0.1rem 0.2rem !important;}
    h1 {font-size: 1.5rem !important; margin-bottom: 0.3rem !important;}
    h2 {font-size: 1.2rem !important; margin-bottom: 0.2rem !important;}
    h3 {font-size: 1rem !important; margin-bottom: 0.2rem !important;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Data Exploration")

st.markdown("Upload a dataset to explore and analyze your data.")

uploaded_file = st.file_uploader("Upload your dataset (CSV)", type=["csv"])

if uploaded_file is not None:
    try:
        # Read the CSV file
        df = pd.read_csv(uploaded_file)
        
        # Store original dataframe in session state
        if 'original_df' not in st.session_state:
            st.session_state['original_df'] = df.copy()
        
        # ============================================================
        # SECTION 1: Datetime Column Selection
        # ============================================================
        with st.expander("📅 1. Datetime Column Selection", expanded=True):
            all_columns = ["None"] + list(df.columns)
            datetime_col = st.selectbox(
                "Select the datetime column (if any):",
                options=all_columns,
                index=0,
                help="If your dataset has a datetime column, select it here to enable time series analysis."
            )
            
            # Parse datetime if selected
            if datetime_col != "None":
                try:
                    df[datetime_col] = pd.to_datetime(df[datetime_col])
                    st.success(f"✅ Column '{datetime_col}' successfully parsed as datetime.")
                except Exception as e:
                    st.warning(f"⚠️ Could not parse '{datetime_col}' as datetime: {e}")
                    datetime_col = "None"
        
        # ============================================================
        # SECTION 2: Data Preview
        # ============================================================
        with st.expander("👁️ 2. Data Preview", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Rows", df.shape[0])
            with col2:
                st.metric("Columns", df.shape[1])
            with col3:
                st.metric("Memory Usage", f"{df.memory_usage(deep=True).sum() / 1024:.2f} KB")
            
            st.dataframe(df.head(20), use_container_width=True)
        
        # ============================================================
        # SECTION 3: Variable Summary
        # ============================================================
        with st.expander("📊 3. Variable Summary", expanded=True):
            # Classify columns
            summary_data = []
            numerical_cols = []
            categorical_cols = []
            datetime_cols_list = []
            
            for col in df.columns:
                col_dtype = df[col].dtype
                missing_count = df[col].isna().sum()
                missing_pct = (missing_count / len(df)) * 100
                unique_count = df[col].nunique()
                
                # Determine variable type
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    var_type = "Datetime"
                    datetime_cols_list.append(col)
                elif pd.api.types.is_numeric_dtype(df[col]):
                    var_type = "Numerical"
                    numerical_cols.append(col)
                else:
                    # Try to convert to numeric
                    try:
                        df[col] = pd.to_numeric(df[col], errors='raise')
                        var_type = "Numerical (converted)"
                        numerical_cols.append(col)
                    except:
                        # Check if it could be datetime
                        if col != datetime_col:
                            try:
                                pd.to_datetime(df[col].dropna().head(10))
                                var_type = "Potential Datetime"
                            except:
                                var_type = "Categorical"
                                categorical_cols.append(col)
                        else:
                            var_type = "Categorical"
                            categorical_cols.append(col)
                
                summary_data.append({
                    "Column": col,
                    "Type": var_type,
                    "Dtype": str(col_dtype),
                    "Missing": missing_count,
                    "Missing %": f"{missing_pct:.2f}%",
                    "Unique": unique_count,
                    "Sample": str(df[col].dropna().iloc[0]) if len(df[col].dropna()) > 0 else "N/A"
                })
            
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, use_container_width=True)
            
            # Missing values visualization
            st.markdown("#### Missing Values")
            missing_data = df.isnull().sum()
            missing_data = missing_data[missing_data > 0]
            
            if len(missing_data) > 0:
                fig_missing = px.bar(
                    x=missing_data.index,
                    y=missing_data.values,
                    labels={'x': 'Column', 'y': 'Missing Count'},
                    title='Missing Values per Column',
                    color=missing_data.values,
                    color_continuous_scale='Reds'
                )
                fig_missing.update_layout(height=400)
                st.plotly_chart(fig_missing, use_container_width=True)
            else:
                st.success("✅ No missing values in the dataset!")
        
        # Filter numerical columns (exclude datetime) - do this once for all sections
        num_cols_for_dist = [c for c in numerical_cols if c != datetime_col]
        
        # ============================================================
        # SECTION 4: Distributions
        # ============================================================
        with st.expander("📈 4. Variable Distributions", expanded=False):
            if num_cols_for_dist:
                st.markdown("#### Numerical Variables")
                
                # Create distribution plots in a grid
                n_cols = min(3, len(num_cols_for_dist))
                n_rows = (len(num_cols_for_dist) + n_cols - 1) // n_cols
                
                for row_idx in range(n_rows):
                    cols = st.columns(n_cols)
                    for col_idx in range(n_cols):
                        var_idx = row_idx * n_cols + col_idx
                        if var_idx < len(num_cols_for_dist):
                            var_name = num_cols_for_dist[var_idx]
                            with cols[col_idx]:
                                fig = px.histogram(
                                    df, 
                                    x=var_name,
                                    title=f'{var_name}',
                                    marginal="box",
                                    nbins=30
                                )
                                fig.update_layout(
                                    height=300,
                                    showlegend=False,
                                    margin=dict(l=20, r=20, t=40, b=20)
                                )
                                st.plotly_chart(fig, use_container_width=True)
            
            if categorical_cols:
                st.markdown("#### Categorical Variables")
                
                # Limit to top 10 categories for each variable
                for cat_col in categorical_cols[:5]:  # Limit to first 5 categorical columns
                    value_counts = df[cat_col].value_counts().head(10)
                    fig = px.bar(
                        x=value_counts.index.astype(str),
                        y=value_counts.values,
                        labels={'x': cat_col, 'y': 'Count'},
                        title=f'Distribution of {cat_col} (Top 10)'
                    )
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)
        
        # ============================================================
        # SECTION 5: Time Series Visualization
        # ============================================================
        with st.expander("⏱️ 5. Time Series Visualization", expanded=False):
            if datetime_col != "None":
                # Sort by datetime
                df_sorted = df.sort_values(by=datetime_col)
                n_points = len(df_sorted)
                
                st.info(f"Dataset has {n_points} data points. {'Using Plotly (interactive)' if n_points < 4000 else 'Using Seaborn (static) for performance'}.")
                
                # Select variables to plot
                ts_vars = st.multiselect(
                    "Select variables to visualize as time series:",
                    options=num_cols_for_dist,
                    default=num_cols_for_dist[:min(3, len(num_cols_for_dist))]
                )
                
                if ts_vars:
                    if n_points < 4000:
                        # Use Plotly for interactive visualization
                        for var in ts_vars:
                            fig = px.line(
                                df_sorted,
                                x=datetime_col,
                                y=var,
                                title=f'{var} over Time'
                            )
                            fig.update_layout(
                                height=350,
                                xaxis_title="Time",
                                yaxis_title=var,
                                hovermode='x unified'
                            )
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        # Use Seaborn/Matplotlib for large datasets
                        for var in ts_vars:
                            fig, ax = plt.subplots(figsize=(12, 4))
                            ax.plot(df_sorted[datetime_col], df_sorted[var], linewidth=0.5)
                            ax.set_xlabel("Time")
                            ax.set_ylabel(var)
                            ax.set_title(f'{var} over Time')
                            plt.xticks(rotation=45)
                            plt.tight_layout()
                            st.pyplot(fig)
                            plt.close()
                        
                        st.caption("Using static plots for better performance with large datasets (>4000 points).")
            else:
                st.info("Select a datetime column in Section 1 to enable time series visualization.")
        
        # ============================================================
        # SECTION 6: Correlation Matrix
        # ============================================================
        with st.expander("🔗 6. Correlation Matrix", expanded=False):
            if len(num_cols_for_dist) > 1:
                # Calculate correlation matrix using only numeric data
                numeric_df = df[num_cols_for_dist].select_dtypes(include=[np.number])
                corr_matrix = numeric_df.corr()
                
                # Get column names as lists
                x_labels = corr_matrix.columns.tolist()
                y_labels = corr_matrix.index.tolist()
                
                # Get correlation values as a 2D list
                z_values = corr_matrix.values.tolist()
                
                # Create annotation text
                z_text = [[f'{val:.2f}' for val in row] for row in z_values]
                
                # Create heatmap using go.Heatmap for more control
                fig_corr = go.Figure(data=go.Heatmap(
                    z=z_values,
                    x=x_labels,
                    y=y_labels,
                    colorscale='RdBu_r',
                    zmin=-1,
                    zmax=1,
                    text=z_text,
                    texttemplate='%{text}',
                    textfont={"size": 10},
                    hovertemplate='%{x} vs %{y}: %{z:.3f}<extra></extra>'
                ))
                
                fig_corr.update_layout(
                    title='Correlation Matrix',
                    height=max(400, len(x_labels) * 40),
                    width=max(600, len(x_labels) * 50),
                    xaxis=dict(tickangle=45),
                    yaxis=dict(autorange='reversed')
                )
                
                st.plotly_chart(fig_corr, use_container_width=True)
                
                # Show highly correlated pairs
                st.markdown("#### Highly Correlated Pairs (|r| > 0.7)")
                high_corr = []
                for i in range(len(corr_matrix.columns)):
                    for j in range(i+1, len(corr_matrix.columns)):
                        corr_val = corr_matrix.iloc[i, j]
                        if not np.isnan(corr_val) and abs(corr_val) > 0.7:
                            high_corr.append({
                                "Variable 1": corr_matrix.columns[i],
                                "Variable 2": corr_matrix.columns[j],
                                "Correlation": f"{corr_val:.3f}"
                            })
                
                if high_corr:
                    st.dataframe(pd.DataFrame(high_corr), use_container_width=True)
                else:
                    st.info("No highly correlated pairs found (|r| > 0.7)")
            else:
                st.warning("Need at least 2 numerical columns for correlation analysis.")
        
        # ============================================================
        # SECTION 7: Statistical Summary
        # ============================================================
        with st.expander("📋 7. Statistical Summary", expanded=False):
            if num_cols_for_dist:
                numeric_df = df[num_cols_for_dist].select_dtypes(include=[np.number])
                stats_df = numeric_df.describe().T
                stats_df['skewness'] = numeric_df.skew()
                stats_df['kurtosis'] = numeric_df.kurtosis()
                st.dataframe(stats_df.round(3), use_container_width=True)
            else:
                st.warning("No numerical columns available for statistical summary.")

    except Exception as e:
        st.error(f"Error loading file: {e}")
        import traceback
        st.code(traceback.format_exc())
