import plotly.graph_objects as go
import plotly.io as pio

pio.templates["NZ_Calc"] = go.layout.Template(
    layout={
        'font': {'family': 'arial',
                 'size': 14,
                 'color': "#0000cd",
                 },
        'colorway': ['#fa8072', '#40e0d0', '#dc143c', '#008080', '#00bfff'],
        'plot_bgcolor': '#f5f5f5', 
    }
)