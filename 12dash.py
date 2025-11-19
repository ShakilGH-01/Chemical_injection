from dash import Dash, dcc, html
from dash.dependencies import Output, Input
import plotly.graph_objs as go
import json
import numpy as np
import threading

# --- GPIO Setup ---
try:
    import RPi.GPIO as GPIO
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    MOTOR1_PIN = 27   # can be change with pi
    MOTOR2_PIN = 22   # can be change with pi

    GPIO.setup(MOTOR1_PIN, GPIO.OUT)
    GPIO.setup(MOTOR2_PIN, GPIO.OUT)

    # Relay is ACTIVE-LOW: False = ON, True = OFF
    def set_tower_light(status):
        if status == 'normal':
            GPIO.output(MOTOR1_PIN, False)  # ON
            GPIO.output(MOTOR2_PIN, True)   # OFF

        elif status == 'warning':
            GPIO.output(MOTOR1_PIN, False)  # ON
            GPIO.output(MOTOR2_PIN, False)  # ON

        elif status == 'critical':
            GPIO.output(MOTOR1_PIN, True)   # OFF
            GPIO.output(MOTOR2_PIN, False)  # ON

        else:
            GPIO.output(MOTOR1_PIN, True)   # OFF
            GPIO.output(MOTOR2_PIN, True)   # OFF

except ImportError:
    print("RPi.GPIO not available — using mock GPIO.")

    def set_tower_light(status):
        print(f"[MOCK GPIO] Active-LOW Logic | Status: {status}")


# --- Dash application ---
app = Dash(__name__)

app.layout = html.Div([
    html.H1(
        "The Smart Chemical Injection System",
        style={
            'textAlign': 'center',
            'color': 'white',
            'backgroundColor': 'blue',
            'height': '8vh',
            'lineHeight': '8vh',
            'margin': '0',
        }
    ),

    html.Div([
        html.Div([
            dcc.Graph(
                id='pressure-temp-graph',
                style={'height': '100%', 'width': '100%'},
                config={'displayModeBar': False, 'staticPlot': True}
            )
        ], style={
            'flex': '1',
            'backgroundColor': 'white',
            'padding': '20px',
            'borderRadius': '10px',
            'boxShadow': '0 4px 10px rgba(0,0,0,0.1)',
            'marginBottom': '10px',
            'height': '46vh',
        }),

        html.Div([
            html.Div([
                html.H4("Current pH", style={'color': 'blue', 'textAlign': 'center'}),
                dcc.Graph(
                    id='pressure-gauge',
                    style={'height': '100%', 'width': '100%'},
                    config={'displayModeBar': False, 'staticPlot': True}
                )
            ], style={
                'backgroundColor': 'white',
                'padding': '15px',
                'borderRadius': '10px',
                'boxShadow': '0 4px 8px rgba(0,0,0,0.1)',
                'marginRight': '10px',
                'flex': '1'
            }),

            html.Div([
                html.H4("Conductivity (µS/cm)", style={'color': 'goldenrod', 'textAlign': 'center'}),
                dcc.Graph(
                    id='temperature-gauge',
                    style={'height': '100%', 'width': '100%'},
                    config={'displayModeBar': False, 'staticPlot': True}
                )
            ], style={
                'backgroundColor': 'white',
                'padding': '15px',
                'borderRadius': '10px',
                'boxShadow': '0 4px 8px rgba(0,0,0,0.1)',
                'flex': '1'
            }),
        ], style={'display': 'flex', 'flex': '1', 'height': '46vh'}),
    ], style={
        'display': 'flex',
        'flexDirection': 'column',
        'height': '92vh',
        'padding': '0 30px 30px 30px',
        'backgroundColor': 'white'
    }),

    html.Div(
        id='warning-popup',
        children="",
        style={
            'position': 'fixed',
            'top': '100px',
            'right': '100px',
            'backgroundColor': 'rgba(255,0,0,0.85)',
            'color': 'white',
            'padding': '15px 25px',
            'borderRadius': '8px',
            'fontWeight': 'bold',
            'fontSize': '16px',
            'zIndex': 9999,
            'display': 'none'
        }
    ),

    dcc.Interval(id='interval-component', interval=1000, n_intervals=0)
])


# --- Load JSON sensor data ---
def load_data():
    try:
        with open('sensor_data.json') as f:
            return json.load(f)
    except:
        return []


def gpio_thread(status):
    set_tower_light(status)


@app.callback(
    Output('pressure-temp-graph', 'figure'),
    Output('pressure-gauge', 'figure'),
    Output('temperature-gauge', 'figure'),
    Output('warning-popup', 'children'),
    Output('warning-popup', 'style'),
    Input('interval-component', 'n_intervals')
)
def update_graph(n):
    data = load_data()
    if not data:
        empty = go.Figure()
        return empty, empty, empty, "", {'display': 'none'}

    times = np.array([d['time'] for d in data])
    ph_values = np.array([d['ph'] for d in data])
    conductivity_values = np.array([d['conductivity'] for d in data])

    # Trend prediction
    alert_status = 'normal'
    alert_message = ""

    threshold_warning = 7.5
    threshold_critical = 8.5

    traces = [
        go.Scatter(x=times, y=ph_values, mode='lines', name='pH', line=dict(color='blue')),
        go.Scatter(x=times, y=conductivity_values, mode='lines', name='Conductivity', yaxis='y2', line=dict(color='goldenrod'))
    ]

    if len(times) > 10:
        slope, intercept = np.polyfit(times, ph_values, 1)
        future = np.arange(times[-1], times[-1] + 60)
        pred = slope * future + intercept

        traces.append(go.Scatter(x=future, y=pred, mode='lines', name='Prediction', line=dict(color='red', dash='dot')))

        max_pred = max(pred)
        if max_pred > threshold_critical:
            alert_status = 'critical'
            alert_message = "⚠ CRITICAL: pH predicted to exceed limit!"
        elif max_pred > threshold_warning:
            alert_status = 'warning'
            alert_message = "⚠ WARNING: pH approaching limit."

    layout = go.Layout(
        title='Sensor Data',
        xaxis=dict(title='Time'),
        yaxis=dict(title='pH', color='blue'),
        yaxis2=dict(title='Conductivity (µS/cm)', overlaying='y', side='right', color='goldenrod'),
        template='plotly_white'
    )

    fig_main = go.Figure(data=traces, layout=layout)

    # Gauges
    fig_ph = go.Figure(go.Indicator(
        mode="gauge+number",
        value=ph_values[-1],
        gauge={'axis': {'range': [7.5, 8.5]}, 'bar': {'color': 'blue'}}
    ))

    fig_cond = go.Figure(go.Indicator(
        mode="gauge+number",
        value=conductivity_values[-1],
        gauge={'axis': {'range': [0, 100]}, 'bar': {'color': 'goldenrod'}}
    ))

    # Run GPIO in background
    threading.Thread(target=gpio_thread, args=(alert_status,), daemon=True).start()

    popup_style = {'display': 'block'} if alert_status != 'normal' else {'display': 'none'}

    return fig_main, fig_ph, fig_cond, alert_message, popup_style


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8050)
