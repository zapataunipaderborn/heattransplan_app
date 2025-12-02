# Pinch Tool
# Python EST Template

One of the first things after creating your repo is to provide some short information about the repo and the code it contains.
**Describe your project in one or two sentences here (and now)!!!**


# Table of contents
- [Python EST Template](#python-est-template)
- [Table of contents](#table-of-contents)
  - [Description](#description)
  - [Installation](#installation)
      - [Virtual environments](#virtual-environments)
        - [Creating a venv in the terminal:](#creating-a-venv-in-the-terminal)
        - [Creating a venv in VS Code:](#creating-a-venv-in-vs-code)
        - [Creating a venv in PyCharm:](#creating-a-venv-in-pycharm)
      - [Installing pip packages (Best practise)](#installing-pip-packages-best-practise)
  - [Usage](#usage)

## Description
Here you are asked to provide a detailed project description about your repository.
This contains the purpose and structure of your project.

## Installation
When building a larger project, that depends on multiple packages a detailed description on how to set up your environment might be necessary.
This is your job...


The following two sections give you a quick overview on best practises on "workspace management" for python coding...enjoy!

#### Virtual environments
When programming different projects over longer periods of time, it can happen that more and more packages are installed, some of which are no longer needed because the corresponding repos have long since been deleted.
This can become a problem when it comes to storage space on your device and will cause the size of your Python installation to grow rapidly.

To solve this problem [virtual environments](https://docs.python.org/3/library/venv.html) (`venv`) come into play.
These `venv` create a project related virtual python interpreter where the packages are installed, meaning if you delete the project (or more specific the `.venv` folder) all installed packages are deleted as well.

Therefore it is suggested to create a `.venv` for each project.

##### Creating a venv in the terminal:

***Due to some windows-related bullshit the following steps may not work in the PowerShell. Instead use the good old Terminal ("Eingabeaufforderung")!***

1. To create a virtual environment using the terminal simply navigate into the project folder or open the terminal directly in this location
2. Run the following command to create a new virtual environment: `python -m venv .venv`
3. Activate your environment for the workspace by executing the following command: `.venv\Scripts\activate`
   
You are now working in your virtual environment, congrats! :)


##### Creating a venv in VS Code:
1. Install the Python Environment Manager extension. After installation the python-symbol should occur in the sidebar on the left side.

2. Press on the python icon in the sidebar, then click on the plus sign in your workspace environment section (top left) and select `Venv` in the opening pop-up.

3. Use your general python installation as your interpreter, when asked.

4. Now a new `venv` should be created and a workspace environment called `.venv (...)` should be displayed.

##### Creating a venv in PyCharm:

**@Henning Rahlf** can you update the section for pycharm please?

#### Installing pip packages (Best practise)
[Pip](https://pip.pypa.io/en/stable/) is one of the most used package manager for python.
To organize your imported packages and make the required packages visible for other users a common way is to use a `requirements.txt` file.
This file is included in this template by default.

Whenever adding an import to your source code, you should also update your `requirements.txt` by simply add your package name to a new line.
```
## requirements.txt
matplotlib
numpy
pandas
...
``` 
If your code relies on a specific version of an imported package (and you want to maintain compatibility) you can also specifiy the version as shown below:
```
numpy==1.21.2
```
*Note: You can also use expressions like `>`, `<`, `>=`, `<=` to allow certain ranges of package versions.* 

To install the required packages you can now simply run the following command:
```
pip install -r requirements.txt
```
insead of installing each package independently.

## Usage
If required, add instructions on how to use the software here...