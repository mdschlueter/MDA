# In[12]:


import dash
from dash import Dash, html, dcc, callback, Output, Input
import dash_ag_grid as dag
import pandas as pd
import numpy as np
from datetime import datetime, timedelta 
import plotly.express as px
import plotly.graph_objects as go
import dash_bootstrap_components as dbc

import matplotlib.pyplot as plt

# In[2]:


import warnings
warnings.filterwarnings("ignore")


# # Experimentation / Sample Graphs

# In[3]:


demographics = pd.read_excel("Demographics_PHI.xlsx")
diagnosis = pd.read_excel("Diagnosis.xlsx")


# In[4]:


overview_df = demographics.groupby(by = ["FACILITY_NAME", "dstype"])[["PATIENT_DISPLAY_ID"]].count().reset_index()
overview_df.columns = ["Facility Name", "dstype", "Number of Patients"]


# In[5]:


df_demo = pd.read_excel("Demographics_PHI.xlsx")
df_diag = pd.read_excel("Diagnosis.xlsx")
df_meds = pd.read_excel("Log.xlsx", sheet_name = "Medication Repeat Group")
df_dev = pd.read_excel("Log.xlsx", sheet_name = "Assistive Device Repeat Group")
df_encounters = pd.read_excel("Encounter.xlsx")
df_trials = pd.read_excel("Encounter.xlsx", sheet_name = "Trial Details")


# In[6]:


onset_cols = [col for col in df_diag.columns if 'onsdt' in col.lower() or 'symdt' in col.lower()]
diag_cols = [col for col in df_diag.columns if 'dgndt' in col.lower() or 'gndt' in col.lower()]

for col in onset_cols + diag_cols:
    df_diag[col] = pd.to_datetime(df_diag[col], errors='coerce')

if onset_cols:
    df_diag['Universal_Onset_Date'] = df_diag[onset_cols].bfill(axis=1).iloc[:, 0]
else:
    df_diag['Universal_Onset_Date'] = pd.NaT # Failsafe if no columns match

if diag_cols:
    df_diag['Universal_Diag_Date'] = df_diag[diag_cols].bfill(axis=1).iloc[:, 0]
else:
    df_diag['Universal_Diag_Date'] = pd.NaT

df_diag['Diagnosis_Delay'] = (df_diag['Universal_Diag_Date'] - df_diag['Universal_Onset_Date'])

df_diag["Diagnosis_Delay"].value_counts()


# In[7]:


if 'medname1-Description' in df_meds.columns:
    df_meds = df_meds[['FACPATID', 'medname1-Description']].dropna()
    df_meds.rename(columns={'medname1-Description': 'Medication'}, inplace=True)


# In[18]:


enc_cols_to_keep = ['FACPATID', "FACILITY_NAME", "encntdt", "dob", "dstype"]
enc_treatment_cols = ["clntrlyn", "prvclntr", "clnresrch" ,"nutrthrp"]
als_specific_cols = ["alsfrsr", "alsfrsdt", "alsfrstl", "speech", "slvatn", "swallow", "handwrit", "gstrstmy", "drshygn", "turnbed", "walking", "clmbstrs", "respinsf", "amblloss", "amblsdt", "spchloss", "spchlsdt", "fstniv", "fstnivdt", "nonivventyn", ]
bmd_specific_cols = ["glcouse", "grth", "grthdat", "ttrsupn", "ttrsuppt", "ttwr10m", "ttwr10pt", "crdmyo"]
dmd_specific_cols = ["glcouse", "grth", "grthdat", "ttrsupn", "ttrsuppt", "ttwr10m", "ttwr10pt", "crdmyo"]
sma_specific_cols = ["smafunc", "headctrl", "rollcmp", "stsup", "crlcmbt", "crl4pt", "stdsprt", "stdunspt", "walkspt", "walkuspt", "clstrage", "cittlscr", "cittlscrpt", "hfmsesc", "hfmsescpt", "rulmcs", "rulmcspt", "respsupdisc", "spiclin", ]
lgmd_specific_cols = ["ttrsupn", "ttcstr", "ttcstrpt", "ttwr10m", "armshldr", "hipslegs", "whlchr"]
fshd_specific_cols = ["ttrsupn", "ttcstr", "ttcstrpt", "ttwr10m", "armshldr", "hipslegs", "whlchr"]
pompe_specific_cols = ["ttrsupn", "ttcstr", "ttcstrpt", "ttwr10m", "armshldr", "hipslegs", "whlchr"]

all_cols = (
    enc_cols_to_keep + 
    enc_treatment_cols + 
    als_specific_cols + 
    bmd_specific_cols + 
    dmd_specific_cols + 
    sma_specific_cols + 
    lgmd_specific_cols + 
    fshd_specific_cols + 
    pompe_specific_cols
)

all_cols_unique = list(dict.fromkeys(all_cols))

df_enc = df_encounters[all_cols_unique].copy()
    
df_enc["encntdt"] = pd.to_datetime(df_enc["encntdt"], errors='coerce')
df_enc["dob"] = pd.to_datetime(df_enc["dob"], errors='coerce')

    
df_enc['Age_at_Encounter'] = ((df_enc["encntdt"] - df_enc['dob']) / 365.25).dt.days

df_enc


# In[19]:


df_dev = df_dev[['FACPATID', 'mobdev', 'asdevstart', 'asdevong']].dropna(subset=['mobdev'])
df_dev


# In[16]:


df_enc.columns


# In[11]:


app = Dash(__name__)

kpi_card_style = {
    'width': '22%', 'display': 'inline-block', 'padding': '20px', 
    'margin': '1%', 'borderRadius': '10px', 'boxShadow': '2px 2px 10px #ddd',
    'textAlign': 'center', 'backgroundColor': '#f9f9f9', 'verticalAlign': 'top'
}

chart_container_style = {
    'width': '32%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '0.5%'
}

app.layout = html.Div([
    html.H1("MOVR Clinical Data Dashboard", style={'textAlign': 'center'}),
    
    # Global Filters
    html.Div([
        html.Div([
            html.Label("Select Disease Type:"),
            dcc.Dropdown(
                id='disease-dropdown',
                options=[{'label': i, 'value': i} for i in df_enc['dstype'].dropna().unique()],
                value=df_enc['dstype'].dropna().unique()[0] if not df_enc['dstype'].dropna().empty else None,
                clearable=False
            )
        ], style={'width': '30%', 'display': 'inline-block', 'padding': '10px'}),
        
        html.Div([
            html.Label("Select Facility (Site):"),
            dcc.Dropdown(
                id='facility-dropdown',
                options=[{'label': 'All Sites', 'value': 'All'}] + 
                        [{'label': f"{i}", 'value': i} for i in df_enc['FACILITY_NAME'].dropna().unique()],
                value='All',
                clearable=False
            )
        ], style={'width': '30%', 'display': 'inline-block', 'padding': '10px'}),
        
        html.Div([
            html.Label("Select Patient (For In-Depth Clinical Tab):"),
            dcc.Dropdown(
                id='patient-dropdown',
                placeholder="Select a patient..."
            )
        ], style={'width': '30%', 'display': 'inline-block', 'padding': '10px'})
    ]),

    html.Hr(),

    # Tabs for Broad vs. Granular View
    dcc.Tabs([
        dcc.Tab(label='Broad Overview', children=[
            html.Div([
                html.Div([html.H4("Total Patients"), html.H2(id='kpi-patients')], style=kpi_card_style),
                html.Div([html.H4("Patients in Trials"), html.H2(id='kpi-trials')], style=kpi_card_style),
                html.Div([html.H4("Patients Using Assistive Devices"), html.H2(id='kpi-dev')], style=kpi_card_style),

            ], style={'display': 'flex', 'justifyContent': 'center'}),
            
            html.Hr(),

            html.Div([
                html.Div([dcc.Graph(id='broad-overview-chart')], style={'width': '48%', 'display': 'inline-block'}),
                html.Div([dcc.Graph(id='top-meds-barchart')], style={'width': '48%', 'display': 'inline-block'})
            ]),
# Second Row
            html.Div([
                html.Div([dcc.Graph(id='asdev-piechart')], style={'width': '48%', 'display': 'inline-block'}),
                html.Div([dcc.Graph(id='ambulation-overview-chart')], style={'width': '48%', 'display': 'inline-block'}) # NEW
            ])
        ]),
        
        dcc.Tab(label='In-Depth Clinical Tracking', children=[
            html.Div([
                html.H3("Longitudinal Disease Progression"),
                dcc.Graph(id='clinical-timeline-chart')
            ])
        ])
    ])
])

# ==========================================
# 3. CALLBACKS
# ==========================================

@app.callback(
    Output('patient-dropdown', 'options'),
    [Input('facility-dropdown', 'value'),
     Input('disease-dropdown', 'value')]
)
def update_patient_dropdown(selected_facility, selected_disease):
    filtered_df = df_enc[df_enc['dstype'] == selected_disease]
    
    if selected_facility != 'All':
        filtered_df = filtered_df[filtered_df['FACILITY_NAME'] == selected_facility]
        
    patients = filtered_df['FACPATID'].dropna().unique()
    return [{'label': str(p), 'value': p} for p in patients]

@app.callback(
    [Output('kpi-patients', 'children'),
     Output('kpi-trials', 'children'),
    Output('kpi-dev', 'children'),
     Output('broad-overview-chart', 'figure'),
     Output('top-meds-barchart', 'figure'),
     Output("asdev-piechart", 'figure'),
     Output("ambulation-overview-chart", "figure")],
    [Input('facility-dropdown', 'value'),
     Input('disease-dropdown', 'value')]
)
def update_broad_overview(selected_facility, selected_disease):
    filtered_df = df_enc[df_enc['dstype'] == selected_disease]
    
    if selected_facility != 'All':
        filtered_df = filtered_df[filtered_df['FACILITY_NAME'] == selected_facility]
    
    filtered_diag = df_diag[df_diag["FACPATID"].isin(filtered_df["FACPATID"])]
    filtered_trials = df_trials[df_diag["FACPATID"].isin(filtered_df["FACPATID"])]
    filtered_dev = df_dev[df_dev["FACPATID"].isin(filtered_df["FACPATID"])]
    filtered_dev = df_dev[df_dev['FACPATID'].isin(filtered_df["FACPATID"])]
    

    valid_patients = filtered_df['FACPATID'].unique()
    total_patients = len(valid_patients)
    trial_patients = filtered_trials['FACPATID'].nunique()
    dev_patients = filtered_dev["FACPATID"].nunique()

    if total_patients != 0:
        trial_percentage = (trial_patients / total_patients) *100
        dev_percentage = (dev_patients / total_patients) * 100
    else:
        trial_percentage = 0
        dev_percentage = 0
    trial_text = f"{trial_percentage: .1f}%"
    dev_text = f"{dev_percentage: .1f}%"

    encounter_counts = filtered_df.groupby('FACPATID').size().reset_index(name='Encounter Count')
    enc_fig = px.histogram(encounter_counts, x='Encounter Count', 
                       title=f"Distribution of Encounters per Patient ({selected_disease})",
                       labels={'Encounter Count': 'Number of Visits'})
    
    filtered_meds = df_meds[df_meds['FACPATID'].isin(filtered_df["FACPATID"])]
    top_10_meds = filtered_meds['Medication'].value_counts().reset_index()
    top_10_meds.columns = ['Medication', 'Patient Count']
    top_10_meds = top_10_meds.head(10)

    meds_fig = px.bar(
            top_10_meds, 
            x='Patient Count', 
            y='Medication', 
            orientation='h',
            title=f"Top 10 Medications ({selected_disease})",
            color='Patient Count',
            color_continuous_scale=px.colors.sequential.Blues
        )
        # Order the y-axis so the most used medication is at the top
    meds_fig.update_layout(yaxis={'categoryorder':'total ascending'})

    device_counts = filtered_dev['mobdev'].value_counts().reset_index()
    device_counts.columns = ['mobdev', 'Count']

    asdev_fig = px.pie(
        device_counts, 
        values='Count', 
        names='mobdev',
        title=f"Assistive Device Distribution ({selected_disease})",
        hole=0.4
    )

    if selected_disease == 'SMA':
        # Map the 1/2 codes to Yes/No
        sma_amb = filtered_df['walkuspt'].map({1: 'Yes', 2: 'No'}).value_counts().reset_index()
        sma_amb.columns = ['Walks Unsupported', 'Patient Count']
        amb_fig = px.bar(sma_amb, x='Walks Unsupported', y='Patient Count', 
                         title="SMA: Walks Unsupported Distribution", color='Walks Unsupported')
                         
    elif selected_disease in ['DMD', 'BMD']:
        # Boxplot for continuous 10m walk times
        amb_fig = px.box(filtered_df, y='ttwr10m', 
                         title=f"{selected_disease}: 10m Walk/Run Times", 
                         labels={'ttwr10m': 'Time (seconds)'})
                         
    elif selected_disease == 'ALS':
        # Assuming 'walking' is a categorical status
        als_amb = filtered_df['walking'].value_counts().reset_index()
        als_amb.columns = ['Walking Status', 'Patient Count']
        amb_fig = px.bar(als_amb, x='Walking Status', y='Patient Count', 
                         title="ALS: Current Walking Status")
    else:
        amb_fig = px.bar(title="Ambulation Data Not Configured for this Disease")


    
    return total_patients, trial_text, dev_text, enc_fig, meds_fig, asdev_fig, amb_fig


@app.callback(
    Output('clinical-timeline-chart', 'figure'),
    [Input('patient-dropdown', 'value'),
     Input('disease-dropdown', 'value')]
)
def update_clinical_timeline(selected_patient, selected_disease):
    if not selected_patient:
        return px.line(title="Please select a patient to view longitudinal data.")
        
    patient_data = df_enc[df_enc['FACPATID'] == selected_patient].sort_values('Age_at_Encounter')
    
    # Dynamically select which metric to plot based on the disease type
    y_metric = None
    if selected_disease == 'ALS' and 'alsfrsr' in patient_data.columns:
        y_metric = 'alsfrsr'  # ALS Functional Rating Scale
    elif selected_disease in ['DMD', 'BMD'] and 'ttwr10m' in patient_data.columns:
        y_metric = 'ttwr10m'  # 10m walk/run time
    elif selected_disease == 'SMA' and 'hfmsesc' in patient_data.columns:
        y_metric = 'hfmsesc'  # Hammersmith Functional Motor Scale
        
    if y_metric and not patient_data[y_metric].isna().all():
        fig = px.line(patient_data, x='Age_at_Encounter', y=y_metric, markers=True,
                      title=f"Longitudinal Progression ({y_metric}) for Patient {selected_patient}",
                      labels={'Age_at_Encounter': 'Age at Encounter (Years)'})
    else:
        # Fallback if specific metrics are empty for this patient
        fig = px.scatter(patient_data, x='Age_at_Encounter', y='encntdt',
                         title=f"Encounter Timeline for Patient {selected_patient} (Missing specific metric data)",
                         labels={'Age_at_Encounter': 'Age at Encounter', 'encntdt': 'Encounter Date'})
    return fig

if __name__ == '__main__':
    app.run(debug=True)

