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
    MOTOR_PIN = 27
    GPIO.setup(MOTOR_PIN, GPIO.OUT)

    def set_tower_light(status):
        GPIO.output(MOTOR_PIN, False)
        if status == 'normal':
            GPIO.output(MOTOR_PIN, False)
        elif status == 'warning':
            GPIO.output(MOTOR_PIN, True)
            GPIO.output(MOTOR_PIN, False)
        elif status == 'critical':
            GPIO.output(MOTOR_PIN, True)
        else:
            GPIO.output(MOTOR_PIN, False)

except ImportError:
    print("RPi.GPIO not available, GPIO functions will be mocked.")

    def set_tower_light(status):
        print(f"[MOCK GPIO] Set tower light to status: {status}")

# --- End GPIO Setup ---

app = Dash(__name__)

app.layout = html.Div([
    html.H1(
        "The Smart Chemical Injection System",
        style={
            'textAlign': 'center',
            'color': 'white',
            'fontFamily': 'Arial, sans-serif',
            'backgroundColor': 'blue',
            'height': '8vh',
            'lineHeight': '8vh',
            'margin': '0',
            'userSelect': 'none'
        }
    ),

    html.Div([
        html.Div([
            dcc.Graph(
                id='pressure-temp-graph',
                style={'height': '100%', 'width': '100%', 'cursor': 'default'},
                config={
                    'displayModeBar': False,
                    'scrollZoom': False,
                    'doubleClick': False,
                    'showTips': False,
                    'staticPlot': True,
                }
            )
        ], style={
            'flex': '1',
            'backgroundColor': 'white',
            'padding': '20px',
            'borderRadius': '10px',
            'boxShadow': '0 4px 10px rgba(0,0,0,0.1)',
            'marginBottom': '10px',
            'height': '46vh',
            'boxSizing': 'border-box',
            'userSelect': 'none'
        }),

        html.Div([
            html.Div([
                html.H4("Current Pressure", style={'color': 'blue', 'textAlign': 'center', 'marginBottom': '12px', 'userSelect': 'none'}),
                dcc.Graph(
                    id='pressure-gauge',
                    style={'height': '100%', 'width': '100%', 'cursor':'default'},
                    config={'displayModeBar': False, 'staticPlot': True}
                )
            ], style={
                'backgroundColor': 'white',
                'padding': '15px',
                'borderRadius': '10px',
                'boxShadow': '0 4px 8px rgba(0,0,0,0.1)',
                'marginRight': '10px',
                'height': '100%',
                'boxSizing': 'border-box',
                'flex': '1',
                'display': 'flex',
                'flexDirection': 'column',
                'userSelect': 'none'
            }),

            html.Div([
                html.H4("Current Temperature", style={'color':'goldenrod', 'textAlign': 'center', 'marginBottom': '12px', 'userSelect': 'none'}),
                dcc.Graph(
                    id='temperature-gauge',
                    style={'height': '100%', 'width': '100%', 'cursor':'default'},
                    config={'displayModeBar': False, 'staticPlot': True}
                )
            ], style={
                'backgroundColor': 'white',
                'padding': '15px',
                'borderRadius': '10px',
                'boxShadow': '0 4px 8px rgba(0,0,0,0.1)',
                'height': '100%',
                'boxSizing': 'border-box',
                'flex': '1',
                'display': 'flex',
                'flexDirection': 'column',
                'userSelect': 'none'
            }),
        ], style={
            'display': 'flex',
            'flex': '1',
            'height': '46vh',
            'boxSizing': 'border-box',
        }),
    ], style={
        'display': 'flex',
        'flexDirection': 'column',
        'height': '92vh',
        'padding': '0 30px 30px 30px',
        'backgroundColor': 'white',
        'userSelect': 'none'
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
            'display': 'none',
            'boxShadow': '0 4px 15px rgba(255,0,0,0.5)',
            'userSelect': 'none'
        }
    ),

    dcc.Interval(id='interval-component', interval=1000, n_intervals=0)
], style={
    'margin': '0',
    'padding': '0',
    'height': '100vh',
    'fontFamily': 'Arial, sans-serif',
    'backgroundColor': 'white',
    'userSelect': 'none'
})


def load_data():
    try:
        with open('sensor_data.json') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error loading data: {e}")
        return []


def gpio_control_thread(status):
    set_tower_light(status)


@app.callback(
    Output('pressure-temp-graph', 'figure'),
    Output('pressure-gauge', 'figure'),
    Output('temperature-gauge', 'figure'),
    Output('warning-popup', 'children'),
    Output('warning-popup', 'style'),
    Input('interval-component', 'n_intervals')
)
def update_graph_live(n):
    data = load_data()
    if not data:
        empty_fig = go.Figure()
        return empty_fig, empty_fig, empty_fig, "", {'display': 'none'}

    times = np.array([d['time'] for d in data])
    pressures = np.array([d['ph'] for d in data])
    temperatures = np.array([d['contectivity'] for d in data])

    trace_pressure = go.Scatter(
        x=times, y=pressures,
        mode='lines+markers',
        name='PH value',
        line=dict(color='blue'),
        marker=dict(color='blue'),
        hoverinfo='skip'
    )

    trace_temperature = go.Scatter(
        x=times, y=temperatures,
        mode='lines+markers',
        name='Contectivity (Ohm)',
        yaxis='y2',
        line=dict(color='goldenrod'),
        marker=dict(color='goldenrod'),
        hoverinfo='skip'
    )

    data_traces = [trace_pressure, trace_temperature]

    threshold_warning = 7 # can be change
    threshold_critical = 10 # can be change

    alert_status = 'normal'
    alert_message = ""

    if len(times) > 10:
        coeffs = np.polyfit(times, pressures, 1)
        slope, intercept = coeffs
        future_times = np.arange(times[-1] + 1, times[-1] + 121)
        preds = slope * future_times + intercept
        trace_pred = go.Scatter(
            x=future_times, y=preds,
            mode='lines',
            name='Predicted PH Value',
            line=dict(color='red', dash='dot'),
            hoverinfo='skip'
        )
        data_traces.append(trace_pred)

        max_pred_pressure = max(preds)
        if max_pred_pressure > threshold_critical:
            alert_status = 'critical'
            alert_message = "⚠️ CRITICAL ALERT: The predicted PH value reaches the critical level"
        elif max_pred_pressure > threshold_warning:
            alert_status = 'warning'
            alert_message = "⚠️ Warning: PH values approaching critical levels."

    layout = go.Layout(
        title='Sensor Data',
        xaxis=dict(title='Time (seconds)', showgrid=True, zeroline=False),
        yaxis=dict(
            title='PH Value',
            color='blue',
            side='left',
            range=[900, 1040],
            showgrid=True
        ),
        yaxis2=dict(
            title='Contectivity ( Ohm)',
            overlaying='y',
            side='right',
            color='goldenrod',
            range=[25, 100],
            showgrid=False
        ),
        legend=dict(x=0, y=1, bgcolor='rgba(255,255,255,0)'),
        template='plotly_white',
        paper_bgcolor='white',
        plot_bgcolor='white',
        margin=dict(l=60, r=60, t=60, b=60),
        hovermode=False,
        dragmode=False,
    )

    fig_graph = go.Figure(data=data_traces, layout=layout)

    fig_pressure_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=pressures[-1],
        gauge={
            'axis': {'range': [900, 1040], 'tickwidth': 2, 'tickcolor':"blue"},
            'bar': {'color': "blue"},
            'bgcolor': 'white',
            'borderwidth': 2,
            'bordercolor': "blue",
            'steps': [
                {'range': [900, 970], 'color': 'lightblue'},
                {'range': [970, 1010], 'color': 'deepskyblue'},
                {'range': [1010, 1040], 'color': 'dodgerblue'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': pressures[-1]
            }
        },
        title={'text': "PH value", 'font': {'color': 'blue', 'size': 18}}
    ))
    fig_pressure_gauge.update_layout(paper_bgcolor='white', margin=dict(t=0, b=0, l=0, r=0))

    fig_temperature_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=temperatures[-1],
        gauge={
            'axis': {'range': [25, 100], 'tickwidth': 2, 'tickcolor': "goldenrod"},
            'bar': {'color': "goldenrod"},
            'bgcolor': 'white',
            'borderwidth': 2,
            'bordercolor': "goldenrod",
            'steps': [
                {'range': [25, 50], 'color': 'khaki'},
                {'range': [50, 80], 'color': 'gold'},
                {'range': [80, 100], 'color': 'darkorange'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': temperatures[-1]
            }
        },
        title={'text': "Temperature (°C)", 'font': {'color': 'goldenrod', 'size': 18}}
    ))
    fig_temperature_gauge.update_layout(paper_bgcolor='white', margin=dict(t=0, b=0, l=0, r=0))

    threading.Thread(target=gpio_control_thread, args=(alert_status,), daemon=True).start()

    if alert_status in ['warning', 'critical']:
        popup_style = {
            'position': 'fixed',
            'top': '20px',
            'right': '20px',
            'backgroundColor': 'rgba(255,0,0,0.85)',
            'color': 'white',
            'padding': '15px 25px',
            'borderRadius': '8px',
            'fontWeight': 'bold',
            'fontSize': '16px',
            'zIndex': 9999,
            'display': 'block',
            'boxShadow': '0 4px 15px rgba(255,0,0,0.5)',
            'userSelect': 'none'
        }
    else:
        popup_style = {'display': 'none'}

    return fig_graph, fig_pressure_gauge, fig_temperature_gauge, alert_message, popup_style


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
