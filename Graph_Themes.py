import plotly.graph_objects as go
import plotly.io as pio

pio.templates["NZ_Calc"] = go.layout.Template(
    layout={
        'font': {'family': 'LibreFranklin',
                 'size': 12,
                 'color': "#0000cd",
                 },
        'colorway': ['#ec7424', '#a4abab'],
    }
)