""" 
Chemical Engineering Aviation Calculator Streamlit Version
Created 20 September 2024
Qiao Yan Soh. qys13@ic.ac.uk 
Last updated 
"""

import plotly.express as px
import pandas as pd
import io
import streamlit as st
import requests
import plotly.io as pio
import GeneralisedFunctions as gf
import Graph_Themes

CalculatorTime_Range = list(range(2019, 2051))

pio.templates.default = "NZ_Calc"

#%% Ambition levels - parameter setting 

# Changes to long haul aviation activity
LH_Demand_AmbLevels = {1: 1.1, 2: 0.9, 3: 0.7, 4: 0.6}

LH_Share_AmbLevels = {
    'First Class' :             {1: 0.003, 2: 0.001, 3: 0, 4: 0},
    'Business Class':           {1: 0.07, 2: 0.03, 3: 0.02, 4: 0.0},
    'Premium Economy Class':    {1: 0.18, 2: 0.219, 3: 0.2, 4: 0}, 
    'Economy Class':            {1: 0.745, 2: 0.75, 3: 0.78, 4: 1},
    'Unknown':                  {1: 0.002, 2: 0.00, 3: 0.0, 4: 0.0},
}

# Changes to short haul aviation activity
SH_Demand_AmbLevels = {1: 1.1, 2: 0.9, 3: 0.7, 4: 0.6}

SH_Share_AmbLevels = {
    'First Class' :             {1: 0.003, 2: 0.001, 3: 0, 4: 0},
    'Business Class':           {1: 0.07, 2: 0.03, 3: 0.02, 4: 0.0},
    'Premium Economy Class':    {1: 0.18, 2: 0.219, 3: 0.2, 4: 0}, 
    'Economy Class':            {1: 0.745, 2: 0.75, 3: 0.78, 4: 1},
    'Unknown':                  {1: 0.002, 2: 0.00, 3: 0.0, 4: 0.0},
}

# Changes to domestic aviation activity
Dom_Demand_AmbLevels = {1: 0.9, 2: 0.7, 3: 0.5, 4: 0}

Dom_Share_AmbLevels = {
    'First Class' :             {1: 0.003, 2: 0.00, 3: 0, 4: 0},
    'Business Class':           {1: 0.07, 2: 0.03, 3: 0.02, 4: 0.00},
    'Premium Economy Class':    {1: 0.18, 2: 0.219, 3: 0.2, 4: 0.0}, 
    'Economy Class':            {1: 0.745, 2: 0.75, 3: 0.78, 4: 1.0},
    'Unknown':                  {1: 0.002, 2: 0.001, 3: 0.000, 4: 0.0},
}

#%% CALCULATION MODULES.

def Travel_EmissionFactors():
    Data_URL = 'https://raw.githubusercontent.com/sohqy/CE_Aviation/refs/heads/main/TravelEmissionFactors_2019Start.csv'
    response = requests.get(Data_URL)
    if response.status_code == 200:
        Data = pd.read_csv(io.StringIO(response.text))
    else:
        print('EmF Data Not loaded')
    # Data = pd.read_csv(Data_URL)
    Data, BaU_ROC = gf.CleanData(Data)

    Categories = list(Data.columns)
    # Categories.remove('Year')

    BaU_EmF = []
    for Category in Categories:
        BaU_EmF.append(gf.BaU_Pathways(Data, Category)) 
    BaU_EmF = pd.concat(BaU_EmF, axis = 1)

    # Combine into GHG
    GHGCategories = []
    for c in Categories:
        ghg_category = c.split('.')[2:4]
        if ghg_category[1] == '':
            ghg_category = ghg_category[0]
        else:
            ghg_category = '.'.join(ghg_category)
        GHGCategories.append(ghg_category)
    GHGCategories = list(set(GHGCategories))        # Remove duplicates
    
    GHG_EmF = {}
    for c in GHGCategories:
        GHG_EmF[c] = sum([BaU_EmF['EmF.'+ ghg + '.' + c + '.'] for ghg in ['CO2', 'N2O', 'CH4']])
    GHG_EmF = pd.DataFrame(GHG_EmF)

    return GHG_EmF.to_json(date_format = 'iso', orient = 'split')

def Generalised_TravelModule(HaulType, Demand_AmbLevels, Share_AmbLevels, DemandLever, DemandSpeed, DemandStart, 
              ClassLever, ClassSpeed, ClassStart, EmF, LeakageFactor):
    if HaulType == 'LongHaul':
        shorthandHaul = 'lH'
    else:
        shorthandHaul = 'sH'
    
    Data_URL = 'https://raw.githubusercontent.com/sohqy/CE_Aviation/refs/heads/main/CE_Data_Public.xlsx'
    Data = pd.read_excel(Data_URL, sheet_name= HaulType)
    Data_Adj = Data.drop(columns = 'Year') / (LeakageFactor/100)
    Data = pd.concat([Data['Year'], Data_Adj], axis = 1)
    Data, BaU_ROC = gf.CleanData(Data)
    Data_Shares = gf.Shares(Data)
    
    EmFactors = gf.JSONtoDF(EmF)
    ProjectedChanges = pd.DataFrame({'Year':CalculatorTime_Range})

    BaU_Demand = gf.BaU_Pathways(Data_Shares, 'Total')          # Unit demand.
    gf.Projections(BaU_Demand, 'Total', Demand_AmbLevels, 
                   DemandLever, DemandSpeed, DemandStart, ProjectedChanges, BaseYear=2022, )
    
    ProjectedDemand = pd.DataFrame({'Year':CalculatorTime_Range})
    ProjectedDemand['Total'] = ProjectedChanges['Total']

    ProjectedShares = pd.DataFrame({'Year':CalculatorTime_Range})

    Categories = list(Data_Shares.columns)
    Categories.remove('Total')

    # ---------- Determine activity by mode and engine
    ActivityByMode = pd.DataFrame({'Year':CalculatorTime_Range})
    Activity_ModeEngine = pd.DataFrame({'Year':CalculatorTime_Range})
    for Category in Categories:
        BaUData = gf.BaU_Pathways(Data_Shares, Category)
        gf.Projections(BaUData, Category, Share_AmbLevels[Category], ClassLever, ClassSpeed, ClassStart, 
                       ProjectedShares, AmbitionsMode='Absolute', BaseYear=2022,)
        ActivityByMode[Category] = ProjectedDemand['Total'] * ProjectedShares[Category]
    Activity_ModeEngine.set_index('Year', inplace = True)
    ActivityByMode.set_index('Year', inplace = True)

    AllEmissions = gf.Aviation_Emissions(Categories, shorthandHaul, EmFactors, ActivityByMode)
    
    return {'Demand': ActivityByMode.to_json(date_format = 'iso', orient = 'split'), 'Emissions':AllEmissions.to_json(date_format = 'iso', orient = 'split')}


def Population_Module(PopulationLever, PopulationSpeed, PopulationStart):
    Data_URL = 'https://raw.githubusercontent.com/sohqy/CE_Aviation/refs/heads/main/CE_Data_Public.xlsx'
    Data = pd.read_excel(Data_URL, sheet_name='Population')
    Data, BaU_ROC = gf.CleanData(Data)
    
    Categories = list(Data.columns)

    ProjectedChanges = pd.DataFrame({'Year':CalculatorTime_Range})
    Population_AmbLevels = {1: 1.2, 2: 1.15, 3: 1.1, 4: 1.0}

    for Category in Categories:
        BaUData = gf.BaU_Pathways(Data, Category,  BaU_ROC = BaU_ROC[Category])
        gf.Projections(BaUData, Category, Population_AmbLevels, PopulationLever, PopulationSpeed, PopulationStart, ProjectedChanges, BaseYear = 2022,)
    
        ProjectedChanges = ProjectedChanges.round(0)
    
    ProjectedChanges.set_index('Year', inplace = True)

    return ProjectedChanges.to_json(date_format='iso', orient='split')

def Sum_TravelEmissions(LH_Emissions, SH_Emissions, DOM_Emissions, Mode = 'Emissions'):
    if Mode == 'Emissions':
        Factor = 1000   # Emissions were calculated in kmCO2e, but presented in tCO2e
    else:
        Factor = 1      # do not convert Psg KM

    LHAviationEmissions = pd.read_json(io.StringIO(LH_Emissions), orient = 'split')
    LH_Total = LHAviationEmissions.sum(axis = 1) / Factor
    LH_Total.rename('Long haul travel', inplace=True)

    SHAviationEmissions = pd.read_json(io.StringIO(SH_Emissions), orient = 'split')
    SH_Total = SHAviationEmissions.sum(axis = 1) / Factor
    SH_Total.rename('Short haul travel', inplace=True)

    DomAviationEmissions = pd.read_json(io.StringIO(DOM_Emissions), orient = 'split')
    Dom_Total = DomAviationEmissions.sum(axis = 1) / Factor
    Dom_Total.rename('Short haul travel', inplace=True)

    Totals = pd.DataFrame({'Long Haul': LH_Total, 'Short Haul': SH_Total, 'Domestic':Dom_Total })
    Totals['Total'] = LH_Total + SH_Total + Dom_Total

    return Totals.to_json(date_format='iso', orient='split')



#%% FIGURE GENERATORS
def CreateFigure_Categorical(CategoriesData, FigTitle, xLabel, yLabel, yRange, xRange = [2019, 2030], ChartType = 'Line'):
    Data = gf.JSONtoDF(CategoriesData)
    Categories = list(Data.columns)

    if ChartType == 'Area':
        fig = px.area(Data, y = Categories, 
                    title = FigTitle,
                    labels = {'value':yLabel, 'index': xLabel}, range_y=yRange, range_x=xRange)
    else:
        fig = px.line(Data, y = Categories, 
                title = FigTitle,
                labels = {'value':yLabel, 'index': xLabel}, range_y=yRange, range_x=xRange) 
    return fig


def Figure_Total_Overview(TotalEmissions):
    Total_AviationEmissions = gf.JSONtoDF(TotalEmissions)
    All_Emissions = Total_AviationEmissions['Total']
    Categorical_Totals = Total_AviationEmissions[['Long Haul', 'Short Haul', 'Domestic']]

    Cumulative_Emissions = All_Emissions.cumsum()

    fig_Cumulative = px.area(Cumulative_Emissions, 
                  labels = {'value':'Cumulative Emissions (tCO2e)'}, range_y=[-1,3.5e4], range_x=[2019, 2030])

    Baseline_Emission = All_Emissions.loc[2022]
    
    fig = px.area(Categorical_Totals, range_y=[-1, 1300], labels = {'value':'Emissions (tCO2e)', 'index':''}, range_x=[2019, 2030])
    fig.add_traces(px.line(All_Emissions, markers=True, color_discrete_sequence= ['black']).data)
    fig.add_hline(y=Baseline_Emission, line_width=2, line_dash="dash", 
        line_color="#ff8c00",  annotation_text="2022/23 Emissions (Baseline)", annotation_font_color="#ff8c00" )
    # fig.add_hline(y = 0.75 * Baseline_Emission, line_width = 2, line_color = '#008080', annotation_font_color="#008080",  
    #               annotation_text="2026 Emissions target (25% reduction)", line_dash = 'dot')
    fig.add_vline(x=2023, line_width=2, line_dash="dash", line_color="#0000cd")
    return fig, fig_Cumulative

def Figure_FTE_Emissions(TotalEmissions, Population):
    Total_AviationEmissions = gf.JSONtoDF(TotalEmissions)
    All_Emissions = Total_AviationEmissions['Total']

    # Sum over all CE population. Should this be just over staff/PG? 
    Population = pd.read_json(io.StringIO(Population), orient = 'split')
    Population_Total = Population.sum(axis = 1) 
    Emissions_FTE = All_Emissions/Population_Total

    # Key targets and values.
    Key_EmissionsFTE_Values = pd.DataFrame({'Baseline (2022)': Emissions_FTE.loc[2022], 'Target': Emissions_FTE.loc[2022] * 0.75, 'Current Selection (2026)': Emissions_FTE.loc[2026]}, index = [0])
    fig = px.bar(Key_EmissionsFTE_Values.T, labels = {'value':'Emissions per person (tCO2e/person)', 'index':''},
                  range_y=[-0.1,1], text_auto='.3f')
    fig.update(layout_showlegend=False)
    return fig

#%% Summary generators
def Return_Selected_Ambitions(AmbitionLevel_Definitions, AmbitionLevel):
    if 1 in AmbitionLevel_Definitions:  # Demand ambitions
        SelectedLevel = (AmbitionLevel_Definitions[AmbitionLevel] - 1) * 100
    else:
        SelectedLevel = {}
        for category in AmbitionLevel_Definitions.keys():
            SelectedLevel[category] = AmbitionLevel_Definitions[category][AmbitionLevel]
    return SelectedLevel

def Changes_Text(SelectedLevel):
    if SelectedLevel > 0:
        Text = 'increases'
    else:
        Text = 'decreases'
    return Text

def Generate_Lever_Summary(LongHaul_Demand, ShortHaul_Demand, Domestic_Demand,
                           LongHaul_Share, ShortHaul_Share, Domestic_Share,):
    LH_DemandSelection = Return_Selected_Ambitions(LH_Demand_AmbLevels, LongHaul_Demand)
    SH_DemandSelection = Return_Selected_Ambitions(SH_Demand_AmbLevels, ShortHaul_Demand)
    Dom_DemandSelection = Return_Selected_Ambitions(LH_Demand_AmbLevels, Domestic_Demand)

    LH_ShareSelection = Return_Selected_Ambitions(LH_Share_AmbLevels, LongHaul_Share)

    SH_ShareSelection = Return_Selected_Ambitions(SH_Share_AmbLevels, ShortHaul_Share)
    Dom_ShareSelection = Return_Selected_Ambitions(Dom_Share_AmbLevels, Domestic_Share)

    Summary = ' ### Lever selection summary \n\n' 
    Summary += 'Long haul demand {} by {:.2f}% \n\n'.format(Changes_Text(LH_DemandSelection), abs(LH_DemandSelection))
    Summary += 'Short haul demand {} by {:.2f}% \n\n'.format( Changes_Text(SH_DemandSelection), abs(SH_DemandSelection))
    Summary += 'Domestic demand {} by {:.2f}% \n\n'.format(Changes_Text(Dom_DemandSelection),abs(Dom_DemandSelection) )

    Summary += '**Long haul travel class shares** \n\n' + '\n\n'.join('{}: {:.1f}%'.format(k,v*100) for k, v in LH_ShareSelection.items())
    Summary += '\n\n**Short haul travel class shares** \n\n' + '\n\n'.join('{}: {:.1f}%'.format(k,v*100) for k, v in SH_ShareSelection.items())
    Summary += '\n\n**Domestic travel class shares** \n\n' + '\n\n'.join('{}: {:.1f}%'.format(k,v*100) for k, v in Dom_ShareSelection.items())

    return Summary 


#%% Application
st.set_page_config(layout="wide")
st.title('Chemical Engineering Aviation Emissions')
st.markdown('''
            ### _This is still in development_
            Welcome to the Chemical Engineering aviation emissions calculator, a tool for supporting CE in making meaningful progress towards more sustainable business travel.
            This is developed using the framework for the Imperial Net-Zero Carbon Calculator. 

            Each lever corresponds to a type of action available, corresponding to an increasing level of of ambition. 
            * **Level 1** corresponds to a minimum abatement effort,
            * **Level 2** is an intermediate scenario where some effort is put into reducing the carbon footprint,
            * **Level 3** is an ambitious but achievable scenario, and
            * **Level 4** is an extraordinarily ambitious scenario.             
            ''')

# ---------- Control side panel
st.sidebar.write('## Control panel')
st.sidebar.write('### How to use')
st.sidebar.markdown('''
                    Each of long-haul, short-haul, and domestic travel have a set of levers associated to adjust their corresponding demand and travel classes used.

                    The proportion of travel captured by Egencia data can also be adjusted separately for each category. 
                    
                    Each lever has an associated _level_, _action start_, and _action speed_.
                    
                    The definitions of the current set of lever selections are summarised on the right. 
                    
                    The start year defines when the mitigating action begins, and the change is applied progressively over the period indicated by the action speed. 
                    ''')
st.sidebar.divider()

# Long haul parameters
LH_Leakage = st.sidebar.number_input(label = '% of long haul aviation captured by Egencia', min_value = 0, max_value = 100, value = 70)
LH_Demand_Lever = st.sidebar.slider(label = 'Long haul Travel Demand', min_value = 1, max_value = 4,value = 1)
LH_Demand_Speed = st.sidebar.number_input(label = 'Long haul demand speed', min_value = 1, max_value = 40, value=2)
LH_Demand_Start = st.sidebar.number_input(label = 'Long haul demand start', min_value = 2024, max_value = 2050, value=2024)
LH_Class_Lever = st.sidebar.slider(label = 'Long Haul Travel Class', min_value = 1, max_value = 4,value = 1)
LH_Class_Speed = st.sidebar.number_input(label = 'Long haul class speed', min_value = 1, max_value = 40, value=2)
LH_Class_Start = st.sidebar.number_input(label = 'Long haul class start', min_value = 2024, max_value = 2050, value=2024)
st.sidebar.divider()

# Short haul parameters
SH_Leakage = st.sidebar.number_input(label = '% of short haul aviation captured by Egencia', min_value = 0, max_value = 100, value = 60)
SH_Demand_Lever = st.sidebar.slider(label = 'Short haul Travel Demand', min_value = 1, max_value = 4,value = 1)
SH_Demand_Speed = st.sidebar.number_input(label = 'Short haul demand speed', min_value = 1, max_value = 40, value=2)
SH_Demand_Start = st.sidebar.number_input(label = 'Short haul demand start', min_value = 2024, max_value = 2050, value=2024)
SH_Class_Lever = st.sidebar.slider(label = 'Short Haul Travel Class', min_value = 1, max_value = 4,value = 1)
SH_Class_Speed = st.sidebar.number_input(label = 'Short haul class speed', min_value = 1, max_value = 40, value=2)
SH_Class_Start = st.sidebar.number_input(label = 'Short haul class start', min_value = 2024, max_value = 2050, value=2024)
st.sidebar.divider()

# Domestic parameters
DOM_Leakage = st.sidebar.number_input(label = '% of domestic aviation captured by Egencia', min_value = 0, max_value = 100, value = 40)
DOM_Demand_Lever = st.sidebar.slider(label = 'Domestic Travel Demand', min_value = 1, max_value = 4,value = 1)
DOM_Demand_Speed = st.sidebar.number_input(label = 'Domestic demand speed', min_value = 1, max_value = 40, value=2)
DOM_Demand_Start = st.sidebar.number_input(label = 'Domestic demand start', min_value = 2024, max_value = 2050, value=2024)
DOM_Class_Lever = st.sidebar.slider(label = 'Domestic Travel Class', min_value = 1, max_value = 4,value = 1)
DOM_Class_Speed = st.sidebar.number_input(label = 'Domestic class speed', min_value = 1, max_value = 40, value=2)
DOM_Class_Start = st.sidebar.number_input(label = 'Domestic class start', min_value = 2024, max_value = 2050, value=2024)
st.sidebar.divider()

# Population levers
Population_Change = st.sidebar.slider(label = 'Population change', min_value = 1, max_value = 4, value = 3)
Population_Speed = st.sidebar.number_input(label = 'Population change speed', min_value = 1, max_value = 40, value=2)
Population_Start = st.sidebar.number_input(label = 'Population change start', min_value = 2024, max_value = 2050, value=2024)


# ---------- Generate data 
Population = Population_Module(Population_Change, Population_Speed, Population_Start)
EmF = Travel_EmissionFactors()
LH_Data = Generalised_TravelModule('LongHaul',LH_Demand_AmbLevels, LH_Share_AmbLevels, LH_Demand_Lever, LH_Demand_Speed, LH_Demand_Start, LH_Class_Lever, LH_Class_Speed, LH_Class_Start, EmF, LH_Leakage)
SH_Data = Generalised_TravelModule('ShortHaul', SH_Demand_AmbLevels, SH_Share_AmbLevels, SH_Demand_Lever, SH_Demand_Speed, SH_Demand_Start, SH_Class_Lever, SH_Class_Speed, SH_Class_Start, EmF, SH_Leakage)
DOM_Data = Generalised_TravelModule('Domestic', Dom_Demand_AmbLevels, Dom_Share_AmbLevels, DOM_Demand_Lever, DOM_Demand_Speed, DOM_Demand_Start, DOM_Class_Lever, DOM_Class_Speed, DOM_Class_Start, EmF, DOM_Leakage)
Total_Emissions = Sum_TravelEmissions(LH_Data['Emissions'], SH_Data['Emissions'], DOM_Data['Emissions'])
Total_Demand = Sum_TravelEmissions(LH_Data['Demand'], SH_Data['Demand'], DOM_Data['Demand'], Mode = 'Demand')

# ---------- Generate figures
Figure_Population = CreateFigure_Categorical(Population, 'Population', '', 'Persons', [-1, 1500], ChartType='Area')
Figure_Emissions, Figure_Cumulative = Figure_Total_Overview(Total_Emissions)
Figure_LH = CreateFigure_Categorical(LH_Data['Emissions'], 'Long haul aviation emissions', '', 'Emissions (kgCO2e)', [-1,8.1e5] )
Figure_SH = CreateFigure_Categorical(SH_Data['Emissions'], 'Short haul aviation emissions', '', 'Emissions (kgCO2e)', [-1,6e3] )
Figure_DOM = CreateFigure_Categorical(DOM_Data['Emissions'], 'Domestic aviation emissions', '', 'Emissions (kgCO2e)', [-1,6e3] )
Figure_FTE = Figure_FTE_Emissions(Total_Emissions, Population)

Figure_Demand = CreateFigure_Categorical(Total_Demand, 'Total Demand', '', 'Psg KM', [-1,4.3e6])

# ---------- Page body layout
Body_Column, Summary_Column = st.columns([0.7, 0.3], gap = 'large')
with Body_Column:
    Overview_Page, Details_Page, Pop_Page = st.tabs(["Overview", "Emissions by categories", "Population and Demand"])
    Overview_Page.plotly_chart(Figure_Emissions, theme = 'streamlit')
    Overview_Page.plotly_chart(Figure_FTE, theme = 'streamlit')
    Overview_Page.plotly_chart(Figure_Cumulative, theme = 'streamlit')

    Details_Page.plotly_chart(Figure_LH, theme = 'streamlit')
    Details_Page.plotly_chart(Figure_SH, theme = 'streamlit')
    Details_Page.plotly_chart(Figure_DOM, theme = 'streamlit')

    Pop_Page.plotly_chart(Figure_Population, theme = 'streamlit')
    Pop_Page.plotly_chart(Figure_Demand, theme = 'streamlit')

Summary_Column.write(Generate_Lever_Summary(LH_Demand_Lever, SH_Demand_Lever, DOM_Demand_Lever,
                                            LH_Class_Lever, SH_Class_Lever, DOM_Class_Lever))
# %%
