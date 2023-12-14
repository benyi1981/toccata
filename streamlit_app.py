#######################
# Import libraries
import streamlit as st
import json
import pandas as pd
import altair as alt
import plotly.express as px
from data_processing import get_financial_quarter, get_financial_year, get_financial_year_quarter
import folium
import geopandas as gpd
from branca.colormap import linear
from streamlit_folium import folium_static

#######################
# Page configuration
st.set_page_config(
    page_title="Toccata Churn Dashboard",
    #page_icon="🏂",
    layout="wide",
    initial_sidebar_state="expanded")

alt.themes.enable("dark")

#######################
# CSS styling
st.markdown("""
<style>

[data-testid="block-container"] {
    padding-left: 2rem;
    padding-right: 2rem;
    padding-top: 1rem;
    padding-bottom: 0rem;
    margin-bottom: -7rem;
}

[data-testid="stVerticalBlock"] {
    padding-left: 0rem;
    padding-right: 0rem;
}

[data-testid="stMetric"] {
    background-color: #393939;
    text-align: center;
    padding: 25px 0;
}

[data-testid="stMetricLabel"] {
  display: flex;
  justify-content: center;
  align-items: center;
}

[data-testid="stMetricDeltaIcon-Up"] {
    position: relative;
    left: 38%;
    -webkit-transform: translateX(-50%);
    -ms-transform: translateX(-50%);
    transform: translateX(-50%);
}

[data-testid="stMetricDeltaIcon-Down"] {
    position: relative;
    left: 38%;
    -webkit-transform: translateX(-50%);
    -ms-transform: translateX(-50%);
    transform: translateX(-50%);
}

</style>
""", unsafe_allow_html=True)


#######################
# Load data configuration

# Function to load the configuration
def load_config():
    with open('config.json') as config_file:
        data = json.load(config_file)
    return data

# Load the configuration
config = load_config()

customer_data_filepath = config["file_paths"]["customer_file"]
geography_filepath = config["file_paths"]["geography_file"]
au_geo_json = config["file_paths"]["au_geo_json"]

#######################
# Load data
df_customer = pd.read_excel(customer_data_filepath)
df_geography = pd.read_csv(geography_filepath)
with open(au_geo_json) as f:
    australia_geojson = json.load(f)

# Creating a dictionary to map postcodes to states based on the highest state count for each postcode
postcode_state_map = df_geography.groupby('postcode')['state'].agg(lambda x: x.value_counts().idxmax()).to_dict()

# Customer join cohort
df_customer['join_year'] = df_customer['join_date'].dt.year
df_customer['join_month'] = df_customer['join_date'].dt.month
df_customer['join_quarter'] = df_customer['join_month'].apply(get_financial_quarter)
df_customer['join_fin_yr'] = df_customer['join_date'].apply(get_financial_year)
df_customer['join_fin_qtr'] = df_customer[['join_fin_yr','join_quarter']].apply(get_financial_year_quarter, axis=1)
df_customer['state'] = df_customer['postcode'].map(postcode_state_map)

customer_join_year = sorted(df_customer['join_year'].unique().tolist())
customer_join_fin_year = sorted(df_customer['join_fin_yr'].unique().tolist())
customer_join_fin_qtr = sorted(df_customer['join_fin_qtr'].unique().tolist())
customer_state = sorted(df_customer['state'].unique().tolist())
customer_status = sorted(df_customer['status'].unique().tolist())


#######################
# Sidebar

# Function to display a multi-select as a dropdown
import streamlit as st

# Sidebar
with st.sidebar:
    st.title('Toccata AI Churn Dashboard')

    # Reset button
    if st.button('Reset Filters'):
        st.session_state['selected_year'] = customer_join_year
        st.session_state['selected_fin_year'] = customer_join_fin_year
        st.session_state['selected_fin_qtr'] = customer_join_fin_qtr
        st.session_state['selected_state'] = customer_state
        st.session_state['selected_customer_status'] = ['Normal', 'Closed']
        st.session_state['selected_color_theme'] = 'blues'

    # Helper function to apply filter if not empty
    def apply_filter(df, column, values):
        if values:
            return df[df[column].isin(values)]
        return df

    # Select a customer join year with "All" option
    selected_year = st.multiselect('Customer Join Years', customer_join_year, default=customer_join_year, key='selected_year')
    df_filtered = apply_filter(df_customer, 'join_year', selected_year)

    # Select a customer join financial year with "All" option
    selected_fin_year = st.multiselect('Customer Join Financial Years', customer_join_fin_year, default=customer_join_fin_year, key='selected_fin_year')
    df_filtered = apply_filter(df_filtered, 'join_fin_yr', selected_fin_year)

    # Select a customer join financial year and quarter with "All" option
    selected_fin_qtr = st.multiselect('Customer Join FY and Quarters', customer_join_fin_qtr, default=customer_join_fin_qtr, key='selected_fin_qtr')
    df_filtered = apply_filter(df_filtered, 'join_fin_qtr', selected_fin_qtr)

    # Select states
    selected_state = st.multiselect('Select state(s)', customer_state, default=customer_state, key='selected_state')
    df_filtered = apply_filter(df_filtered, 'state', selected_state)

    # Select Customer Status
    selected_customer_status = st.multiselect('Select Customer Status', customer_status, default=customer_status, key='selected_customer_status')
    df_filtered = apply_filter(df_filtered, 'status', selected_customer_status)


#######################
# Plots



# Heatmap
# def make_heatmap(input_df, input_y, input_x, input_color, input_color_theme):
#     heatmap = alt.Chart(input_df).mark_rect().encode(
#             y=alt.Y(f'{input_y}:O', axis=alt.Axis(title="Year", titleFontSize=18, titlePadding=15, titleFontWeight=900, labelAngle=0)),
#             x=alt.X(f'{input_x}:O', axis=alt.Axis(title="", titleFontSize=18, titlePadding=15, titleFontWeight=900)),
#             color=alt.Color(f'max({input_color}):Q',
#                              legend=None,
#                              scale=alt.Scale(scheme=input_color_theme)),
#             stroke=alt.value('black'),
#             strokeWidth=alt.value(0.25),
#         ).properties(width=900
#         ).configure_axis(
#         labelFontSize=12,
#         titleFontSize=12
#         ) 
#     # height=300
#     return heatmap

# Choropleth map
def make_choropleth(input_df, input_id, input_column):
    # Convert GeoJSON to a GeoDataFrame
    gdf = gpd.GeoDataFrame.from_features(australia_geojson['features'])

    # Merge the DataFrame with the GeoDataFrame
    merged_gdf = gdf.merge(input_df, left_on='ste_iso3166_code', right_on=input_id)

    # Convert the merged GeoDataFrame back to GeoJSON
    merged_geojson = merged_gdf.to_json()

    # Create a base map
    m = folium.Map(location=[-25.2744, 133.7751], zoom_start=4, tiles='Stamen Toner', attr='Map data © OpenStreetMap contributors')

    # Prepare a color scale
    max_count = max(input_df[input_column])
    min_count = min(input_df[input_column])
    color_scale = linear.YlGnBu_09.scale(min_count, max_count)

    # Create a GeoJson object with tooltips
    folium.GeoJson(
        merged_geojson,
        style_function=lambda feature: {
            'fillColor': color_scale(feature['properties'][input_column]) if feature['properties'][input_column] is not None else 'gray',
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.7
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['ste_iso3166_code', input_column],
            aliases=['State Code: ', 'Customer Count: '],
            localize=True
        )
    ).add_to(m)

    # Add color scale to map
    color_scale.caption = input_column
    color_scale.add_to(m)

    return m


# Donut chart
def make_donut(input_response, input_text, input_color):
  if input_color == 'blue':
      chart_color = ['#29b5e8', '#155F7A']
  if input_color == 'green':
      chart_color = ['#27AE60', '#12783D']
  if input_color == 'orange':
      chart_color = ['#F39C12', '#875A12']
  if input_color == 'red':
      chart_color = ['#E74C3C', '#781F16']
    
  source = pd.DataFrame({
      "Topic": ['', input_text],
      "% value": [100-input_response, input_response]
  })
  source_bg = pd.DataFrame({
      "Topic": ['', input_text],
      "% value": [100, 0]
  })
    
  plot = alt.Chart(source).mark_arc(innerRadius=55, cornerRadius=25).encode(
      theta="% value",
      color= alt.Color("Topic:N",
                      scale=alt.Scale(
                          #domain=['A', 'B'],
                          domain=[input_text, ''],
                          # range=['#29b5e8', '#155F7A']),  # 31333F
                          range=chart_color),
                      legend=None),
  ).properties(width=140)
    
  text = plot.mark_text(align='center', color="#29b5e8", font="Lato", fontSize=38, fontWeight=700, fontStyle="italic").encode(text=alt.value(f'{input_response} %'))
  plot_bg = alt.Chart(source_bg).mark_arc(innerRadius=55, cornerRadius=20).encode(
      theta="% value",
      color= alt.Color("Topic:N",
                      scale=alt.Scale(
                          # domain=['A', 'B'],
                          domain=[input_text, ''],
                          range=chart_color),  # 31333F
                      legend=None),
  ).properties(width=140)
  return plot_bg + plot + text

# Convert population to text 
def format_number(num):
    if num > 1000000:
        if not num % 1000000:
            return f'{num // 1000000} M'
        return f'{round(num / 1000000, 1)} M'
    return f'{num // 1000} K'

# Calculation year-over-year population migrations
# def calculate_population_difference(input_df, input_year):
#   selected_year_data = input_df[input_df['year'] == input_year].reset_index()
#   previous_year_data = input_df[input_df['year'] == input_year - 1].reset_index()
#   selected_year_data['population_difference'] = selected_year_data.population.sub(previous_year_data.population, fill_value=0)
#   selected_year_data['population_difference_absolute'] = abs(selected_year_data['population_difference'])
#   return pd.concat([selected_year_data.states, selected_year_data.id, selected_year_data.population, selected_year_data.population_difference, selected_year_data.population_difference_absolute], axis=1).sort_values(by="population_difference", ascending=False)


#######################
# Dashboard Main Panel
row_1_col = st.columns((1, 5, 2))

# with row_1_col[0]:
#     st.markdown('#### Gains/Losses')

#     df_population_difference_sorted = calculate_population_difference(df_reshaped, selected_year)

#     if selected_year > 2010:
#         first_state_name = df_population_difference_sorted.states.iloc[0]
#         first_state_population = format_number(df_population_difference_sorted.population.iloc[0])
#         first_state_delta = format_number(df_population_difference_sorted.population_difference.iloc[0])
#     else:
#         first_state_name = '-'
#         first_state_population = '-'
#         first_state_delta = ''
#     st.metric(label=first_state_name, value=first_state_population, delta=first_state_delta)

#     if selected_year > 2010:
#         last_state_name = df_population_difference_sorted.states.iloc[-1]
#         last_state_population = format_number(df_population_difference_sorted.population.iloc[-1])   
#         last_state_delta = format_number(df_population_difference_sorted.population_difference.iloc[-1])   
#     else:
#         last_state_name = '-'
#         last_state_population = '-'
#         last_state_delta = ''
#     st.metric(label=last_state_name, value=last_state_population, delta=last_state_delta)

    
#     st.markdown('#### States Migration')
#     # Filter states with population difference > 50000
#     df_greater_50000 = df_population_difference_sorted[df_population_difference_sorted.population_difference_absolute > 50000]
#     # % of States with population difference > 50000
#     states_migration = int((len(df_greater_50000)/df_population_difference_sorted.states.nunique())*100)
#     donut_chart = make_donut(states_migration, 'States Migration', 'orange')
#     st.altair_chart(donut_chart)


with row_1_col[1]:
    st.markdown('#### Total Customer Count')

    df_reshaped = df_filtered.groupby('state').size().reset_index(name='customer_count')

    choropleth = make_choropleth(df_reshaped, 'state', 'customer_count')
    #st.plotly_chart(choropleth, use_container_width=True)
    folium_static(choropleth)
    
    # heatmap = make_heatmap(df_reshaped, 'year', 'state', 'customer_count', selected_color_theme)
    # st.altair_chart(heatmap, use_container_width=True)
    

with row_1_col[2]:
    st.markdown('#### Top States')
    df_reshaped = df_filtered.groupby('state').size().reset_index(name='customer_count')
    st.dataframe(df_reshaped,
                 column_order=("state", "customer_count"),
                 hide_index=True,
                 width=None,
                 column_config={
                    "states": st.column_config.TextColumn(
                        "States",
                    ),
                    "customer_count": st.column_config.ProgressColumn(
                        "Customer Count",
                        format="%f",
                        min_value=0,
                        max_value=max(df_reshaped.customer_count),
                     )}
                 )
    
    with st.expander('About'):
        st.write('''
            placeholder text
            ''')