# MATHEMATICAL DEFINITION:
# z_{n+1} = z_n^p + c
# If |z| > 2, the point escapes.

# z[mask] is the z_n (the current state)
# z[mask]**intPower is the z_n^p (the power iteration)
# c[mask] is the constant c (the pixel coordinate)

import numpy as np
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, ctx, no_update
import subprocess
import os

# --- THE SAFE PORT JANITOR ---
def cleanup_port(port):
    current_pid = os.getpid()
    print(f"Cleaning up port {port}...")
    try:
        result = subprocess.run(["lsof", "-ti", f":{port}"], capture_output=True, text=True)
        output = result.stdout.strip()
        if not output:
            print(f"No processes found on port {port}. Proceeding...")
            return
        pids = output.split('\n')
        for pid_str in pids:
            pid = int(pid_str)
            if pid != current_pid:
                print(f"Terminating zombie process {pid} on port {port}...")
                subprocess.run(["kill", "-9", str(pid)])
            else:
                print(f"Skipping self (PID {pid}) to avoid suicide.")
        print("Port is clean.")
    except Exception as e:
        print(f"Cleanup error: {e}")

# --- The Mathematical Engine ---
def calculate_fractal(h, w, y_range, x_range, iterations, intPower, julia_constant=None):
    x = np.linspace(x_range[0], x_range[1], w)
    y = np.linspace(y_range[0], y_range[1], h)
    X, Y = np.meshgrid(x, y)
    points = X + 1j * Y
    c = points if julia_constant is None else np.full(points.shape, julia_constant, dtype=complex)
    z = np.zeros(points.shape, dtype=complex) if julia_constant is None else points.copy()

    fractal = np.zeros(c.shape, dtype=int)
    mask = np.full(c.shape, True, dtype=bool)

    for i in range(iterations):
        z[mask] = z[mask]**intPower + c[mask]
        newly_escaped = (np.abs(z) >= 2) & mask
        fractal[newly_escaped] = i
        mask[np.abs(z) >= 2] = False
        
    return fractal

# --- Initialize the Dash App ---
app = Dash(__name__)

julia_constants = {
    'classic-1': ('Classic Beauty (-0.4 + 0.6i)', -0.4 + 0.6j),
    'classic-2': ('Classic Beauty (-0.8 + 0.156i)', -0.8 + 0.156j),
    'douady-rabbit': ('Douady Rabbit', -0.123 + 0.745j),
    'dendrite': ('Dendrite', 1j),
    'san-marco': ('San Marco', -0.75 + 0.1j),
}

color_options = [
    {'label': c, 'value': c} for c in ['aggrnyl', 'agsunset', 'algae', 'amp', 'armyrose', 'balance',
             'blackbody', 'bluered', 'blues', 'blugrn', 'bluyl', 'brbg',
             'brwnyl', 'bugn', 'bupu', 'burg', 'burgyl', 'cividis', 'curl',
             'darkmint', 'deep', 'delta', 'dense', 'earth', 'edge', 'electric',
             'emrld', 'fall', 'geyser', 'gnbu', 'gray', 'greens', 'greys',
             'haline', 'hot', 'hsv', 'ice', 'icefire', 'inferno', 'jet',
             'magenta', 'magma', 'matter', 'mint', 'mrybm', 'mygbm', 'oranges',
             'orrd', 'oryel', 'oxy', 'peach', 'phase', 'picnic', 'pinkyl',
             'piyg', 'plasma', 'plotly3', 'portland', 'prgn', 'pubu', 'pubugn',
             'puor', 'purd', 'purp', 'purples', 'purpor', 'rainbow', 'rdbu',
             'rdgy', 'rdpu', 'rdylbu', 'rdylgn', 'redor', 'reds', 'solar',
             'spectral', 'speed', 'sunset', 'sunsetdark', 'teal', 'tealgrn',
             'tealrose', 'tempo', 'temps', 'thermal', 'tropic', 'turbid',
             'turbo', 'twilight', 'viridis', 'ylgn', 'ylgnbu', 'ylorbr',
             'ylorrd']
]

app.layout = html.Div([
    html.H1("Mandelbrot & Julia Set Explorer", style={'textAlign': 'center', 'marginBottom': '20px'}),
    
    html.Div([
        # LEFT SIDE: The Graph
        html.Div([
            dcc.Graph(
                id='mandelbrot-graph',
                config={'displayModeBar': True, 'scrollZoom': True},
                style={'height': '80vh'}
            )
        ], style={'flex': '1', 'display': 'flex', 'justifyContent': 'center'}),

        # RIGHT SIDE: The Sidebar (Controls)
        html.Div([
            html.H4("Settings", style={'textAlign': 'center', 'borderBottom': '1px solid #ccc'}),
            
            html.Div([
                html.Label("Fractal Set", style={'fontWeight': 'bold'}),
                dcc.Dropdown(
                    id='fractal-dropdown',
                    options=[
                        {'label': 'Mandelbrot', 'value': 'mandelbrot'},
                        *[
                            {'label': label, 'value': key}
                            for key, (label, _) in julia_constants.items()
                        ],
                    ],
                    value='mandelbrot',
                    clearable=False
                ),
            ], style={'paddingBottom': '20px'}),

            html.Div([
                html.Label("Color Palette", style={'fontWeight': 'bold'}),
                dcc.Dropdown(
                    id='color-dropdown',
                    options=color_options,
                    value='turbo',
                    clearable=False
                ),
            ], style={'paddingBottom': '20px'}),
            
            html.Div([
                html.Label("Iterations", style={'fontWeight': 'bold'}),
                dcc.Input(id='iter-input', type='number', value=100, step=10, style={'width': '100%'}),
            ], style={'paddingBottom': '20px'}),
            
            html.Div([
                html.Label("Power (z^n)", style={'fontWeight': 'bold'}),
                dcc.Input(id='power-input', type='number', value=2, step=1, style={'width': '100%'}),
            ], style={'paddingBottom': '20px'}),

            html.Hr(),
            html.Label("Zoom & Position", style={'fontWeight': 'bold', 'color': 'blue'}),
            
            html.Div([
                html.Label("Zoom Factor:", style={'fontSize': '12px'}),
                dcc.Input(id='zoom-input', type='number', value=1, step=0.5, style={'width': '100%'}),
            ], style={'paddingBottom': '10px'}),

            html.Div([
                html.Label("Center X:", style={'fontSize': '12px'}),
                dcc.Input(id='cx-input', type='number', value=-0.5, step=0.001, style={'width': '100%'}),
            ], style={'paddingBottom': '10px'}),

            html.Div([
                html.Label("Center Y:", style={'fontSize': '12px'}),
                dcc.Input(id='cy-input', type='number', value=0, step=0.001, style={'width': '100%'}),
            ]),
            
        ], style={'width': '300px', 'padding': '20px', 'borderLeft': '1px solid #ccc', 'marginLeft': '20px', 'height': '80vh', 'overflowY': 'auto'})

    ], style={'display': 'flex', 'flexDirection': 'row', 'alignItems': 'flex-start', 'justifyContent': 'center', 'padding': '10px'})
])

@app.callback(
    [Output('mandelbrot-graph', 'figure'),
     Output('cx-input', 'value'),
     Output('cy-input', 'value'),
     Output('zoom-input', 'value')],
    [Input('fractal-dropdown', 'value'),
     Input('color-dropdown', 'value'),
     Input('iter-input', 'value'),
     Input('power-input', 'value'),
     Input('zoom-input', 'value'),
     Input('cx-input', 'value'),
     Input('cy-input', 'value'),
     Input('mandelbrot-graph', 'clickData'),
     Input('mandelbrot-graph', 'relayoutData')]
)
def update_graph(selected_fractal, selected_color, selected_iterations, selected_power, zoom, cx, cy, click_data, relayout_data):
    cx_output = no_update
    cy_output = no_update
    zoom_output = no_update

    selected_fractal = 'mandelbrot' if selected_fractal is None else selected_fractal
    selected_iterations = 100 if selected_iterations is None else max(1, int(selected_iterations))
    selected_power = 2 if selected_power is None else max(1, int(selected_power))
    zoom = 1 if zoom is None else max(float(zoom), 0.0001)
    cx = -0.5 if cx is None else float(cx)
    cy = 0 if cy is None else float(cy)
    selected_color = 'turbo' if selected_color is None else selected_color

    if ctx.triggered_id == 'fractal-dropdown':
        cx = -0.5 if selected_fractal == 'mandelbrot' else 0
        cy = 0
        zoom = 1
        cx_output = cx
        cy_output = cy
        zoom_output = zoom

    if ctx.triggered_id == 'mandelbrot-graph':
        if click_data and click_data.get('points'):
            point = click_data['points'][0]
            cx = point.get('x', cx)
            cy = point.get('y', cy)
            cx_output = cx
            cy_output = cy

    # Base resolution
    width, height = 1000, 700 
    
    # 1. Define the "World" view (the full fractal)
    base_x_min, base_x_max = -2.25, 1.25
    base_y_min, base_y_max = -1.5, 1.5
    
    world_width = base_x_max - base_x_min
    world_height = base_y_max - base_y_min

    triggered_props = ctx.triggered_prop_ids
    if 'mandelbrot-graph.relayoutData' in triggered_props and relayout_data:
        x_min = relayout_data.get('xaxis.range[0]')
        x_max = relayout_data.get('xaxis.range[1]')
        y_min = relayout_data.get('yaxis.range[0]')
        y_max = relayout_data.get('yaxis.range[1]')
        if all(isinstance(value, (int, float)) for value in (x_min, x_max)):
            range_width = abs(x_max - x_min)
            if range_width > 0:
                zoom = max(world_width / range_width, 0.0001)
                cx = (x_min + x_max) / 2
                zoom_output = zoom
                cx_output = cx
                if all(isinstance(value, (int, float)) for value in (y_min, y_max)):
                    cy = (y_min + y_max) / 2
                    cy_output = cy
    
    # 2. Apply the Zoom logic
    # We shrink the viewport around the center point based on the zoom factor
    half_w = (world_width / max(zoom, 0.0001)) / 2
    half_h = (world_height / max(zoom, 0.0001)) / 2
    
    x_range = (cx - half_w, cx + half_w)
    y_range = (cy - half_h, cy + half_h)

    # 3. Calculate the math
    julia_constant = None
    if selected_fractal != 'mandelbrot':
        _, julia_constant = julia_constants[selected_fractal]
    fractal = calculate_fractal(
        height, width, y_range, x_range, selected_iterations, selected_power, julia_constant
    )

    x_axis = np.linspace(x_range[0], x_range[1], width)
    y_axis = np.linspace(y_range[0], y_range[1], height)

    fig = go.Figure(data=go.Heatmap(
        z=fractal,
        x=x_axis,
        y=y_axis,
        colorscale=selected_color,
        colorbar=dict(title='Iterations'),
        connectgaps=False
    ))

    figure_title = 'Mandelbrot Set'
    if julia_constant is not None:
        julia_label, _ = julia_constants[selected_fractal]
        figure_title = (
            f"Julia Set: {julia_label} "
            f"(c={julia_constant.real:g}{julia_constant.imag:+g}i)"
        )

    fig.update_layout(
        title=figure_title,
        xaxis_title='Real (Re)',
        yaxis_title='Imaginary (Im)',
        width=width,
        height=height,
        yaxis=dict(scaleanchor="x", scaleratio=1),
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    return fig, cx_output, cy_output, zoom_output

if __name__ == '__main__':
    cleanup_port(8050)
    print("Server starting on http://127.0.0.1:8050/")
    app.run(debug=True, use_reloader=False)
