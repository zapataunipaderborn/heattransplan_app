from CoolProp.CoolProp import PropsSI

class ThermodynamicProperties():

    def get_hprime(T, fluid = 'Water'):
        TK = float(T)+273.15
        return PropsSI('H', 'T', TK, 'Q', 0, fluid) / 1000  # kJ/kg
    
    def get_hdouble_prime(T, fluid = 'Water'):
        TK = float(T)+273.15
        return PropsSI('H', 'T', TK, 'Q', 1, fluid) / 1000  # kJ/kg
    
    def get_vprime(T, fluid = 'Water'):
        TK = float(T)+273.15
        rho_liq = PropsSI('D', 'T', TK, 'Q', 0, fluid)  # kg/m3
        return 1 / rho_liq  # m3/kg
    
    def get_latentheat(T, fluid = 'Water'):
        TK = float(T)+273.15
        return (PropsSI('H', 'T', TK, 'Q', 1, fluid) / 1000) - (PropsSI('H', 'T', TK, 'Q', 0, fluid) / 1000) # kJ/kg
        