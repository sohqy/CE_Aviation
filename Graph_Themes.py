import plotly.graph_objects as go
import plotly.io as pio

pio.templates["NZ_Calc"] = go.layout.Template(
    layout={
        'font': {'family': 'libre-franklin',
                 'size': 12,
                 'color': "#0000cd",
                 },
        'colorway': ['#fa8072', '#40e0d0', '#f0e68c'],
    }
)