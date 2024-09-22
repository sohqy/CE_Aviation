""" 
CODE TITLE HERE 
Created 
Qiao Yan Soh. qys13@ic.ac.uk 
Last updated 
"""

import numpy as np
import pandas as pd 
import io

def CleanData(Data):
    """
    Ensures data read has no nans, transforms strings into flaots, and calculates a BaU rate of change.

    Args:
        Data (pandas dataframe): a dataframe read from csv files containing data with year indices and columns as different categories. 

    Returns:
        _type_: _description_
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
        AmbitionLevel (_type_): _description_

    Returns:
        _type_: _description_
    """
    # Ambition_ROC = Def_AmbitionLevels[AmbitionLevel]**(1/AmbitionSpeed) - 1
    AmbitionLevel_UB = np.ceil(AmbitionLevel)
    AmbitionLevel_LB = np.floor(AmbitionLevel)
    if AmbitionLevel_UB == AmbitionLevel_LB:
        AmbitionLevel_UB += 1
    return AmbitionLevel_UB, AmbitionLevel_LB

def BaU_Pathways(Data, Category, BaU_ROC = None, CalculatorTime_Range = list(range(2018, 2051))):
    # Determine BaU pathway
    Projected_BaUData = pd.DataFrame({'Year':CalculatorTime_Range})
    BaUData = Projected_BaUData.join(Data[Category], on='Year')        
    FinalPoint = BaUData[Category][BaUData[Category].notnull()].values[-1]      # Final non NA
    FinalIdx = np.where(BaUData[Category] == FinalPoint)[0][0]
    if BaU_ROC is not None:
        FinalYear = BaUData['Year'][FinalIdx]
        BaUData[Category] = BaUData[Category].fillna(value = FinalPoint * (1+BaU_ROC)**(BaUData['Year'] - FinalYear))
    else:
        BaUData[Category] = BaUData[Category].fillna(value = FinalPoint)

    BaUData.set_index('Year', inplace = True)

    return BaUData

def Projections(BaUData, Category, Ambition_Definitions, Level, AmbitionSpeed, AmbitionStart, ProjectedChanges, 
                BaseYear = 2018, AmbitionsMode = 'Percentage'):    

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
    AmbStartValue = BaUData[Category].loc[AmbitionStart-1]
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

def Shares(Data, ):
    Total = Data.sum(axis = 1)
    Categories = list(Data.columns)
    Data_Shares = Data.copy(deep = True)
    for Category in Categories:
        Data_Shares[Category] = Data[Category]/Total
    Data_Shares['Total'] = Total
    return Data_Shares

# def ShareAmbLevels(Categories): TODO how can this be simplified as an input? 

#     return AmbitionLevels

def CheckShareAmbLevels(Share_AmbLevels):
    """
    Makes sure that the ambition levels of the different categories add up to 1.

    Args:
        Share_AmbLevels (_type_): _description_
    """
    Totals = {}
    for Level in range(1,5):
        Totals[Level] = sum([Share_AmbLevels[Category][Level] for Category in Share_AmbLevels.keys()]) 
    return Totals


def Map_ModeEngine(Mode, ActivityByMode, Activity_ModeEngine, EngineShare, AllModeEngines):
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

def JSONtoDF(Var):
    Dataframe = pd.read_json(io.StringIO(Var), orient = 'split')
    return Dataframe