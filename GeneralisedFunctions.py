""" 
Generalised framework for NZ calculator. 
Created August 2024
Qiao Yan Soh. qys13@ic.ac.uk 
Last updated October 2024
"""

import numpy as np
import pandas as pd 
import io

def CleanData(Data):
    """
    Ensures data read has no nans, transforms strings into flaots, and calculates a BaU rate of change.

    Args:
        Data (dataframe): Data with year indices and columns as different categories. 

    Returns:
        (dataframe, float): A dataframe containing cleaned historical data ready for use, and a scalar value corresponding to the Business-as-usual rate of change.
    """
    Modules = list(Data.columns)
    Modules.remove('Year')
    Data.replace({'-':np.nan}, inplace = True)  # Re-code missing data
    Data = Data.astype(float)       # Make sure data is kept in usable format.
    Data.set_index('Year', inplace = True)

    BaU_ROC = (Data[Modules].pct_change(fill_method = None)).mean()

    return Data, BaU_ROC

def Determine_AmbitionLevelBounds(AmbitionLevel):
    """
    Find upper and lower bounds of the ambition levels - required for when this is not set to the integer values.

    Args:
        AmbitionLevel (float): Selected ambition level value.

    Returns:
        tuple: values corresponding to the upper and lower integer bounds of the selected ambition level. 
    """
    AmbitionLevel_UB = np.ceil(AmbitionLevel)
    AmbitionLevel_LB = np.floor(AmbitionLevel)

    # Check if the ambition level provided is an integer value. 
    if AmbitionLevel_UB == AmbitionLevel_LB:
        AmbitionLevel_UB += 1
    return AmbitionLevel_UB, AmbitionLevel_LB

def BaU_Pathways(Data, Category, BaU_ROC = None, CalculatorTime_Range = list(range(2018, 2051))):
    """
    Extrapolates the given historical data to produce a 'business-as-usual' pathway. 
    
    Args:
        Data (dataframe): Historical data for the module. This needs to have years in its index and categories as its columns.
        Category (str): Name of column corresponding to the category of interest.
        BaU_ROC (float, optional): Rate of change calculated from historical data. If not available, the last known historical data point is used. Defaults to None.
        CalculatorTime_Range (list, optional): List corresponding to the time steps used in the calculator. Defaults to list(range(2018, 2051)).

    Returns:
        dataframe: Dataframe with the year as its index, corresponding to the BaU pathway for the given category.
    """
    # Set up output dataframe
    Projected_BaUData = pd.DataFrame({'Year':CalculatorTime_Range})
    BaUData = Projected_BaUData.join(Data[Category], on='Year')        
    
    # Find final historical data point
    FinalPoint = BaUData[Category][BaUData[Category].notnull()].values[-1]      
    FinalIdx = np.where(BaUData[Category] == FinalPoint)[0][0]
    
    # Apply change rates if applicable.
    if BaU_ROC is not None:
        FinalYear = BaUData['Year'][FinalIdx]
        BaUData[Category] = BaUData[Category].fillna(value = FinalPoint * (1+BaU_ROC)**(BaUData['Year'] - FinalYear))
    else:
        BaUData[Category] = BaUData[Category].fillna(value = FinalPoint)

    BaUData.set_index('Year', inplace = True)

    return BaUData

def Projections(BaUData, Category, Ambition_Definitions, Level, AmbitionSpeed, AmbitionStart, ProjectedChanges, 
                BaseYear = 2018, AmbitionsMode = 'Percentage'):    
    """
    Calculates a projected pathway for the given category following the given ambition level, speed, and start year. 

    Args:
        BaUData (dataframe): Business as usual data that includes the given category of interest.
        Category (str): The category of interest in this calculation. 
        Ambition_Definitions (dict): Definition of each level of ambition for the given category.
        Level (float): Selected level of ambition for the category.
        AmbitionSpeed (float): The number of years in which action is to be taken. 
        AmbitionStart (int): The year in which action begins. 
        ProjectedChanges (dataframe): The dataframe which stores the projected pathways. 
        BaseYear (int, optional): The year in which changes are in reference to. Defaults to 2018.
        AmbitionsMode (str, optional): Signifies whether the ambition levels are defined in proportional or absolute terms. Defaults to 'Percentage'.

    Returns:
        dataframe: The dataframe which stores the projected pathways. 
    """
    # Define base year and set up ambition bounds. 
    BaseYear_Value = BaUData[Category].loc[BaseYear]
    AmbitionLevel_UB, AmbitionLevel_LB = Determine_AmbitionLevelBounds(Level)

    if AmbitionsMode == 'Percentage':
        MappedAmbitionLevels = {k: v * BaseYear_Value for k, v in Ambition_Definitions.items()}  # Translate percentages into correct units, if not this is absolute 
    else:
        MappedAmbitionLevels = Ambition_Definitions

    if Level == 4:
        Ambition_Value = MappedAmbitionLevels[Level]
    else:
        Ambition_Value = (AmbitionLevel_UB - Level) * MappedAmbitionLevels[AmbitionLevel_LB] + (Level - AmbitionLevel_LB) * MappedAmbitionLevels[AmbitionLevel_UB]

    # Recalculate new pathways based on given parameters
    NewData = []
    AmbStartValue = BaUData[Category].loc[AmbitionStart-1]  # Value at the time when action is implemented.

    for y in ProjectedChanges['Year']:
        BaU = BaUData[Category].loc[y]
        if y < AmbitionStart:
            NewData.append(BaU)
        elif y >= AmbitionStart + AmbitionSpeed:
            NewData.append(Ambition_Value)
        else:
            if AmbStartValue == 0:
                Rate = 0
            else:
                Rate = (Ambition_Value/AmbStartValue) ** (1/AmbitionSpeed) - 1
            New_Value = max(AmbStartValue * (1+Rate)**(y - AmbitionStart + 1),0)
            NewData.append(New_Value)
    ProjectedChanges[Category] = NewData

    return ProjectedChanges

def Shares(Data):
    """
    Translates absolute values into shares of the total, across the given categories (columns).

    Args:
        Data (dataframe): Dataframe containing raw data to be transformed into percentages. 

    Returns:
        dataframe: Dataframe containing percentage shares of each category across the given set of columns. 
    """
    Total = Data.sum(axis = 1)          # Find total from which to calculate shares from 
    Categories = list(Data.columns)
    Data_Shares = Data.copy(deep = True)
    for Category in Categories:
        Data_Shares[Category] = Data[Category]/Total
    Data_Shares['Total'] = Total
    return Data_Shares

def CheckShareAmbLevels(Share_AmbLevels):
    """
    Adds up the ambition levels of the different categories. Used to ensure that the defined share ambition levels for each
    category add up to 1.

    Args:
        Share_AmbLevels (dict): Dictionary containing percentage shares of each category.
    """
    Totals = {}
    for Level in range(1,5):
        Totals[Level] = sum([Share_AmbLevels[Category][Level] for Category in Share_AmbLevels.keys()]) 
    return Totals

### TRAVEL SPECIFIC FUNCTIONS 
def Map_ModeEngine(Mode, ActivityByMode, Activity_ModeEngine, EngineShare, AllModeEngines):
    """
    Map possible engine types to each mode of transport and splits the relevant transport activity by the given engine share.

    Args:
        Mode (str): Mode of transport. 
        ActivityByMode (dataframe): Activity levels (in km) of each transport mode. 
        Activity_ModeEngine (dataframe): dataframe that is to be used to store the disagregated activity levels by engine
        EngineShare (dataframe): Share of each engine type by mode. 
        AllModeEngines (list): List of modes and engines considered in the calculation.
    """
    if Mode in ['Car', 'Bus']:
        Engines = ['E', 'H2', 'PHEV', 'IC']
        ModeEngine = [Mode.lower() + m for m in Engines]
        for m in ModeEngine:
            Activity_ModeEngine[m] = ActivityByMode[Mode] * EngineShare[m][0]
            AllModeEngines.append(m)

    elif Mode in ['National Rail (Train)', 'Train']:
        Engines = ['trnPE', 'trnPIC']
        for m in Engines:
            Activity_ModeEngine[m] = ActivityByMode[Mode] * EngineShare[m][0]
            AllModeEngines.append(m)
    
    else:
        if Mode == 'Underground':
            m = 'Udg'
        elif Mode == 'Motorcycle':
            m = 'MtrCyc'
        elif Mode == 'Light Rail':
            m = 'dlr'
        else:
            m = Mode
        Activity_ModeEngine[m] = ActivityByMode[Mode]
        AllModeEngines.append(m)
    
def Calc_TravelEmissions(AllModeEngines, Activity_ModeEngine,  EmFactors, CalculatorTime_Range = list(range(2018, 2051))):
    """
    _summary_

    Args:
        AllModeEngines (_type_): _description_
        Activity_ModeEngine (_type_): _description_
        EmFactors (_type_): _description_
        CalculatorTime_Range (_type_, optional): _description_. Defaults to list(range(2018, 2051)).

    Returns:
        _type_: _description_
    """
    for mode in ['Bicycle', 'Walking', 'Other', 'carH2']:
        if mode in AllModeEngines:
            AllModeEngines.remove(mode)

    ElectricFuels = ['Udg', 'busE', 'carE', 'trnPE', 'busPHEV', 'carPHEV', 'dlr']
    H2Fuels = ['busH2', 'carH2']

    AllEmissions =  pd.DataFrame({'Year':CalculatorTime_Range})
    AllEmissions.set_index('Year', inplace = True)
    for m in AllModeEngines:
        if m in ElectricFuels:
            Fuel = '.fElc'
        elif m == 'Taxi':
            Fuel = ''
        elif m in H2Fuels:
            Fuel = '.fH2G'
        elif m == 'Coach':
            Fuel = '.fFsLP'
        else:
            Fuel = '.fFsLD'
            
        AllEmissions[m] = Activity_ModeEngine[m] *  EmFactors[m + Fuel] 
    return AllEmissions

def Aviation_Emissions(Categories, Haul, EmFactors, ActivityByMode, CalculatorTime_Range = list(range(2018, 2051))):
    RenameMap = {'First Class': 'First',
                 'Business Class': 'Biz',
                 'Premium Economy Class': 'Prem',
                 'Economy Class': 'Econ',
                 'Unknown': 'Unknown'
                 }
    AllEmissions =  pd.DataFrame({'Year':CalculatorTime_Range})
    AllEmissions.set_index('Year', inplace = True)
    for Category in Categories:
        EmFName ='avi' + Haul + 'Con' + RenameMap[Category] + '.fFsLD' 
        AllEmissions[Category] = EmFactors[EmFName] * ActivityByMode[Category]

    return AllEmissions


def PopulationCategories(Mode):
    StudentCategories = ['UG', 'PGT', 'PGR', 'Part Time PGT', 'Part Time PGR']
    FeeCategories = ['Home', 'Overseas']
    StaffCategories = ['Academic', 'Research', 'Support']
    
    if 'Students' not in Mode:
        Relevant_Populations = StaffCategories
    elif 'All' in Mode: # All students
        Relevant_Populations = [S + ' ' + F for S in StudentCategories for F in FeeCategories]
    elif 'Home' in Mode:
        Relevant_Populations = [S + ' ' + 'Home' for S in StudentCategories]
    else:
        Relevant_Populations = [S + ' ' + 'Overseas' for S in StudentCategories]

    return Relevant_Populations


def Module_DemandShares(Data, Population, EmF, 
                              Demand_AmbLevels, Share_AmbLevels, 
                              PopulationMode, Travel_Type = 'Non-Aviation',
                              DemandLever = 1, DemandSpeed = 10, DemandStart = 2025, 
                              SharesLever = 1, SharesSpeed = 5, SharesStart = 2035, 
                              ShareofEngineTypes = None, CalculatorTime_Range = list(range(2018, 2051)),
                              ExtDemand = None, OutputDemand = False, Details = False):
    """
    Wrapper function. 

    Args:
        Data (dataframe): _description_
        Population (dataframe): Population pathways. 
        EmF (dataframe): Emission factor pathways. 
        Demand_AmbLevels (dict): _description_
        Share_AmbLevels (dict): _description_
       PopulationMode (str): _description_        Travel_Type (str, optional): _description_. Defaults to 'Non-Aviation'.
        DemandLever (int, optional): _description_. Defaults to 1.
        DemandSpeed (int, optional): _description_. Defaults to 10.
        DemandStart (int, optional): _description_. Defaults to 2025.
        SharesLever (int, optional): _description_. Defaults to 1.
        SharesSpeed (int, optional): _description_. Defaults to 5.
        SharesStart (int, optional): _description_. Defaults to 2035.
        ShareofEngineTypes (_type_, optional): _description_. Defaults to None.
        CalculatorTime_Range (_type_, optional): _description_. Defaults to list(range(2018, 2051)).
        ExtDemand (_type_, optional): _description_. Defaults to None.
        OutputDemand (bool, optional): _description_. Defaults to False.
        Details (bool, optional): _description_. Defaults to False.

    Returns:
        _type_: _description_
    """
    Data, BaU_ROC = CleanData(Data)

    Data_Shares = Shares(Data)   # Transform data into share % of modes, kept in columns

    # Read data from other callbacks. 
    PopulationPathways = pd.read_json(io.StringIO(Population), orient = 'split')
    EmFactors = pd.read_json(io.StringIO(EmF), orient = 'split')
    if ShareofEngineTypes is not None:
        EngineShare = pd.read_json(io.StringIO(ShareofEngineTypes), orient = 'split')

    # Set up demand ambition levels
    ProjectedChanges = pd.DataFrame({'Year':CalculatorTime_Range})

    # ---------- Total Demand
    if ExtDemand is None:
        BaU_Demand = BaU_Pathways(Data_Shares, 'Total')          # Unit demand.
        Projections(BaU_Demand, 'Total', Demand_AmbLevels, DemandLever, DemandSpeed, DemandStart, ProjectedChanges)

        ProjectedDemand = pd.DataFrame({'Year':CalculatorTime_Range})

        RelevantCategories = PopulationCategories(PopulationMode)
        ProjectedDemand['Total'] = ProjectedChanges['Total'] * sum(PopulationPathways[R] for R in RelevantCategories)
    else:
        ProjectedDemand = ExtDemand
        ProjectedDemand.reset_index(inplace = True)

    # ---------- Projected Shares 
    ProjectedShares = pd.DataFrame({'Year':CalculatorTime_Range})

    Categories = list(Data_Shares.columns)
    Categories.remove('Total')
    
    # ---------- Determine activity by mode and engine
    ActivityByMode = pd.DataFrame({'Year':CalculatorTime_Range})
    Activity_ModeEngine = pd.DataFrame({'Year':CalculatorTime_Range})
    AllModeEngines = []
    for Category in Categories:
        BaUData = BaU_Pathways(Data_Shares, Category)
        Projections(BaUData, Category, Share_AmbLevels[Category], SharesLever, SharesSpeed, SharesStart, ProjectedShares, AmbitionsMode='Absolute')
        ActivityByMode[Category] = ProjectedDemand['Total'] * ProjectedShares[Category]
        if Travel_Type == 'Non-Aviation':
            if Category != 'Aviation':
                Map_ModeEngine(Category, ActivityByMode, Activity_ModeEngine, EngineShare, AllModeEngines)
    Activity_ModeEngine.set_index('Year', inplace = True)
    ActivityByMode.set_index('Year', inplace = True)

    # Calculate emissions #
    if Travel_Type == 'Non-Aviation':
        AllEmissions = Calc_TravelEmissions(AllModeEngines, Activity_ModeEngine, EmFactors)
    elif Travel_Type == 'Aviation':
        AllEmissions = Aviation_Emissions(Categories, 'lH', EmFactors, ActivityByMode)
    if OutputDemand == True:
        if Details == True:
            return AllEmissions, ActivityByMode
        else:
            return AllEmissions, ProjectedDemand
    else:
        return AllEmissions

### OTHER FUNCTIONS 
def JSONtoDF(Var):
    """
    Wrapper for reading json data, which are output from the calculation modules, into dataframes to be manipulated. 

    Args:
        Var (obj): variable storing the json representation of the desired dataframe.

    Returns:
        dataframe: information from the json encoding, in a dataframe format. 
    """
    Dataframe = pd.read_json(io.StringIO(Var), orient = 'split')
    return Dataframe


#%% Thoughts for further modules 
# building demand - can probably be implemented similarly to travel demand mods. 
