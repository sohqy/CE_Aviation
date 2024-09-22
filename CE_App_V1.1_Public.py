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

import GeneralisedFunctions as gf

CalculatorTime_Range = list(range(2019, 2051))


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
    'First Class' :             {1: 0.003, 2: 0.001, 3: 0, 4: 0},
    'Business Class':           {1: 0.07, 2: 0.03, 3: 0.02, 4: 0.01},
    'Premium Economy Class':    {1: 0.18, 2: 0.218, 3: 0.2, 4: 0.1}, 
    'Economy Class':            {1: 0.745, 2: 0.75, 3: 0.779, 4: 0.89},
    'Unknown':                  {1: 0.002, 2: 0.001, 3: 0.001, 4: 0.0},
}

#%%

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


def LH_Travel(DemandLever, DemandSpeed, DemandStart, 
              ClassLever, ClassSpeed, ClassStart, EmF,):
    Data_URL = 'https://raw.githubusercontent.com/sohqy/CE_Aviation/refs/heads/main/CE_Data_Public.xlsx'
    Data = pd.read_excel(Data_URL, sheet_name='LongHaul')
    Data, BaU_ROC = gf.CleanData(Data)
    Data_Shares = gf.Shares(Data)
    
    EmFactors = pd.read_json(io.StringIO(EmF), orient = 'split')
    ProjectedChanges = pd.DataFrame({'Year':CalculatorTime_Range})

    BaU_Demand = gf.BaU_Pathways(Data_Shares, 'Total')          # Unit demand.
    gf.Projections(BaU_Demand, 'Total', LH_Demand_AmbLevels, 
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
        gf.Projections(BaUData, Category, LH_Share_AmbLevels[Category], ClassLever, ClassSpeed, ClassStart, 
                       ProjectedShares, AmbitionsMode='Absolute', BaseYear=2022,)
        ActivityByMode[Category] = ProjectedDemand['Total'] * ProjectedShares[Category]
    Activity_ModeEngine.set_index('Year', inplace = True)
    ActivityByMode.set_index('Year', inplace = True)

    AllEmissions = gf.Aviation_Emissions(Categories, 'lH', EmFactors, ActivityByMode)
    
    return AllEmissions.to_json(date_format = 'iso', orient = 'split')

#%% FIGURE GENERATORS

def Figure_LongHaul_Classes(LH_Emissions):
    LHAviationEmissions = pd.read_json(io.StringIO(LH_Emissions), orient = 'split')
    Categories = list(LHAviationEmissions.columns)

    fig = px.line(LHAviationEmissions, y = Categories, 
                  title = 'Long haul aviation emissions',
                 labels = {'value':'Emissions (kgCO2e)'}, range_y=[-1,8.1e5],) 
    return fig

def Figure_Total_Overview(LH_Emissions):
    
    LHAviationEmissions = pd.read_json(io.StringIO(LH_Emissions), orient = 'split')
    LH_Total = LHAviationEmissions.sum(axis = 1) / 1000
    LH_Total.rename('Long haul travel', inplace=True)

    TotalEmissions = LH_Total #+ SH_Total + Dom_Total
    TotalEmissions.rename('Total aviation emissions', inplace=True)
    Cumulative_Emissions = TotalEmissions.cumsum()

    fig_Cumulative = px.area(Cumulative_Emissions, 
                  labels = {'value':'Cumulative Emissions (tCO2e)'}, range_y=[-1,2.5e4])

    Baseline_Emission = TotalEmissions.loc[2022]

    Totals = pd.DataFrame({'Long Haul': LH_Total, }) #'Short Haul': SH_Total, 'Domestic':Dom_Total })
    fig = px.area(Totals, range_y=[-1,1.15e3], labels = {'value':'Emissions (tCO2e)'})
    fig.add_traces(px.line(TotalEmissions, markers=True, color_discrete_sequence= ['black']).data)
    fig.add_hline(y=Baseline_Emission, line_width=2, line_dash="dash", 
        line_color="blue",  annotation_text="2022/23 Emissions (Baseline)", annotation_font_color="blue" )
    fig.add_hline(y = 0.75 * Baseline_Emission, line_width = 2, line_color = 'green', annotation_font_color="green",  
                  annotation_text="2026 Emissions target (25% reduction)", line_dash = 'dot')
    
    return fig, fig_Cumulative


#%% Application
st.set_page_config(layout="wide")
st.title('Chemical Engineering Aviation Emissions')
st.write('Hello this is a page.')

st.sidebar.write('Control panel')
LH_Demand_Lever = st.sidebar.slider(label = 'Long Haul Travel Demand', min_value = 1, max_value = 4,value = 1)
LH_Demand_Speed = st.sidebar.number_input(label = 'Long haul demand speed', min_value = 1, max_value = 40, value=2)
LH_Demand_Start = st.sidebar.number_input(label = 'Long haul demand start', min_value = 2024, max_value = 2050, value=2024)


EmF = Travel_EmissionFactors()
LH_Data = LH_Travel(LH_Demand_Lever, LH_Demand_Speed, LH_Demand_Start, LH_Demand_Lever, 2, 2024, EmF)
Figure_LH = Figure_LongHaul_Classes(LH_Data)
Figure_Emissions, Figure_Cumulative = Figure_Total_Overview(LH_Data)

Body_Column, Summary_Column = st.columns([0.6, 0.4], gap = 'medium')
with Body_Column:
    Overview_Page, Details_Page = st.tabs(["Overview", "Breakdowns"])
    Overview_Page.plotly_chart(Figure_Emissions)
    Overview_Page.plotly_chart(Figure_Cumulative)

    Details_Page.plotly_chart(Figure_LH)

Summary_Column.write('Lever selection summary here')
# %%
