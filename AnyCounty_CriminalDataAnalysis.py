import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import re

# Import
pd_incident_report_df = pd.read_csv('Anycounty Police_Department_Incident_Reports__2018_to_Present_20251117.csv')
case_resolution_report_df = pd.read_csv('Anycounty District_Attorney_Case_Resolutions_20251117.csv')
prosecuted_cases_df = pd.read_excel('Anycounty District_Attorney_Cases_Prosecuted_20251117 FINAL.xlsx')

#--------------
#Number of Incident Types by Year
incident_types_to_review = ['Drug', 'Theft', 'Gun']
incident_types_pattern = '|'.join(incident_types_to_review)

# Filtering
mask = pd_incident_report_df['Incident Description'].str.contains(
    incident_types_pattern, 
    case=False, 
    na=False
)
filtered_pd_df = pd_incident_report_df[mask].copy()

# Categorization/Mapping
conditions = [
    # Check if category contains 'Drug'
    filtered_pd_df['Incident Description'].str.contains('Drug', case=False, na=False),
    # Check if category contains 'Theft'
    filtered_pd_df['Incident Description'].str.contains('Theft', case=False, na=False),
    # Check if category contains 'Gun'
    filtered_pd_df['Incident Description'].str.contains('Gun', case=False, na=False)
]

choices = [
    'Drug Reports',
    'Theft Reports',
    'Gun Reports'
]

filtered_pd_df['Major Category'] = np.select(conditions, choices, default='Other')

# Aggregate Categories
major_category_frequency_df = filtered_pd_df.groupby(
    ['Incident Year', 'Major Category']
).size().reset_index(name='Frequency')

# Ensure 'Incident Year' is numeric
major_category_frequency_df['Incident Year'] = pd.to_numeric(
    major_category_frequency_df['Incident Year'], errors='coerce'
)

# Filter the data to include only 2019 and later
major_category_frequency_df = major_category_frequency_df[
    major_category_frequency_df['Incident Year'] >= 2019
].copy()

major_category_frequency_df['Incident Year'] = major_category_frequency_df['Incident Year'].astype(str)

major_category_frequency_df['Incident Year'] = pd.Categorical(major_category_frequency_df['Incident Year'], 
                                                            categories=sorted(major_category_frequency_df['Incident Year'].unique()), 
                                                            ordered=True)


category_order = ['Theft Reports', 'Drug Reports', 'Gun Reports']

major_category_frequency_df = major_category_frequency_df.sort_values(by=['Major Category', 'Incident Year'])

major_category_frequency_df['Pct Change'] = major_category_frequency_df.groupby('Major Category')['Frequency'].pct_change() * 100


# Subplots (3 rows, 1 column)
fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(12, 18), sharex=True, sharey=False) 

for i, category in enumerate(category_order):
    ax = axes[i]
    
    # Filter data for the current category
    subset_df = major_category_frequency_df[major_category_frequency_df['Major Category'] == category].reset_index(drop=True)
    
    # Plotting
    max_freq = subset_df['Frequency'].max()
    ax.set_ylim(0, max_freq + max_freq * 0.10) 
    
    sns.barplot(
        x='Incident Year',
        y='Frequency',
        data=subset_df,
        ax=ax,
        color=sns.color_palette("viridis")[i + 1]
    )
    
    # Define Buffers
    Y_BUFFER_PERCENT = max_freq * 0.03
    Y_BUFFER_COUNT = max_freq * -0.05
    
    # Add Annotations and Set Title
    for j, row in subset_df.iterrows():
        freq = row['Frequency']
        pct_change = row['Pct Change']
        
        color = 'black'
        text_pct_label = ""
        count_label = f"{freq:,.0f}"
    
        # Percent Label
        if j > 0:
            if pct_change > 0:
                color = 'green'
                text_pct_label = f"↑ +{pct_change:.1f}%"
            elif pct_change < 0:
                color = 'red'
                text_pct_label = f"↓ {pct_change:.1f}%"
            else:
                color = 'gray'
                text_pct_label = f"— 0.0%"
        
        # Labels
        
        # % Annotation
        if text_pct_label:
            ax.text(
                x=j,
                y=freq + Y_BUFFER_PERCENT,
                s=text_pct_label,
                color=color,
                ha='center',
                va='bottom',
                fontsize=12
            )
        
        # Absolute Count Label
        y_position_count = freq + (Y_BUFFER_COUNT if j > 0 else Y_BUFFER_PERCENT)
        
        ax.text(
            x=j,
            y=y_position_count,
            s=count_label,
            color='black',
            ha='center',
            va='bottom',
            fontsize=12
        )
    
        # subplot titles and labels
        ax.set_title(f'Frequency of {category} (2019-2025)', fontsize=14)
        ax.set_ylabel('Case Frequency')

        # Placement for source note
        ax.text(
            x=0.0, 
            y=-0.1,
            s='Source: Anycounty Police Dept. Incident Report Data', 
            transform=ax.transAxes,
            fontsize=9, 
            color='dimgray', 
            ha='left'
        )
        
        # Handle X-axis labels (only on the bottom plot)
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        if i < len(category_order) - 1:
            ax.set_xlabel('')
        else:
            ax.set_xlabel('Incident Year', fontsize=12)

# Adjust layout
plt.tight_layout()

plt.subplots_adjust(hspace=0.3)
plt.savefig('Frequency of Incident Categories per Year_ACDAO.png')

# ---
# AVERAGE TIMELINE - Filing to Disposition

filtered_pd_df['Major Category'] = np.select(conditions, choices, default='Other')

# Standardize
filtered_pd_df['Incident Number'] = filtered_pd_df['Incident Number'].astype(str)

resolution_df = case_resolution_report_df.copy()
resolution_df.rename(columns={'incident_number': 'Incident Number'}, inplace=True)

# Standardize
resolution_df['Incident Number'] = resolution_df['Incident Number'].astype(str)

# Convert dates
resolution_df['Disp Date'] = pd.to_datetime(resolution_df['disposition_date'], errors='coerce')
resolution_df['Filing Date'] = pd.to_datetime(resolution_df['filing_date'], errors='coerce')

# Merge Filtered DFs
merged_timeline_df = pd.merge(
    #Left: Pulling in 'Major Category' along with the ID and Year
    filtered_pd_df[['Incident Number', 'Incident Year', 'Major Category']].drop_duplicates(subset=['Incident Number']),
    # Right: date columns
    resolution_df[['Incident Number', 'Filing Date', 'Disp Date']],
    on='Incident Number',
    how='inner'
)

# Cleaning
merged_timeline_df.dropna(subset=['Filing Date', 'Disp Date'], inplace=True)

# Extract Filing Year
merged_timeline_df['Filing Year'] = merged_timeline_df['Filing Date'].dt.year

# Calculate Time Difference - Filing to Disposition
merged_timeline_df['Time Delta'] = merged_timeline_df['Disp Date'] - merged_timeline_df['Filing Date']

# Convert TimeDelta to Months
merged_timeline_df['Time in Months'] = merged_timeline_df['Time Delta'].dt.days / 30.44

# Filter for target years
target_years = list(range(2019, 2026)) 
merged_timeline_df['Filing Year'] = pd.to_numeric(merged_timeline_df['Filing Year'], errors='coerce')
refined_timeline_df = merged_timeline_df[
    merged_timeline_df['Filing Year'].isin(target_years)
].copy() 

# Ensure 'Filing Year' is categorical
refined_timeline_df['Filing Year'] = refined_timeline_df['Filing Year'].astype(str)

category_order = ['Theft Reports', 'Drug Reports', 'Gun Reports']

# Filter out all rows where 'Time in Months' is less than zero
refined_timeline_df = refined_timeline_df[
    refined_timeline_df['Time in Months'] >= 0
].copy()

# Convert 'Filing Year' to categorical type, with chronological order
year_categories = sorted(refined_timeline_df['Filing Year'].unique())
refined_timeline_df['Filing Year'] = pd.Categorical(
    refined_timeline_df['Filing Year'], 
    categories=year_categories, 
    ordered=True
)
# Sort the DataFrame
refined_timeline_df = refined_timeline_df.sort_values(by=['Major Category', 'Filing Year'])

# Create Subplots
fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(14, 15), sharex=True, sharey=False) 

for i, category in enumerate(category_order):
    ax = axes[i] 
    
    # Filter data for the current category
    subset_df = refined_timeline_df[refined_timeline_df['Major Category'] == category].copy()
    
    sns.boxplot(
        x='Filing Year',
        y='Time in Months',
        data=subset_df,
        ax=ax,
        color=sns.color_palette("Set2")[i] 
    )
    
    # Annotations
    # Median, Q1, and Q3 for each year within the subset
    stats = subset_df.groupby('Filing Year')['Time in Months']
    medians = stats.median()
    q1_values = stats.quantile(0.25)
    q3_values = stats.quantile(0.75)
    
    for j, year_label in enumerate(medians.index):
        median_val = medians.loc[year_label]
        q1_val = q1_values.loc[year_label]
        q3_val = q3_values.loc[year_label]
        
        # Median
        ax.text(j, median_val + 0.5, f'Med: {median_val:.1f}', 
                horizontalalignment='center', size='x-small', color='black', weight='semibold')
        
        # Q1 and Q3 
        ax.text(j, q1_val - 2.0, f'Q1: {q1_val:.1f}', 
                horizontalalignment='center', size='xx-small', color='dimgray')
        ax.text(j, q3_val + 2.0, f'Q3: {q3_val:.1f}', 
                horizontalalignment='center', size='xx-small', color='dimgray')
    
    ax.set_title(f'{category}: Average Filing to Disposition Times in Months (2019-2025)', fontsize=16)
    ax.set_ylabel('Time in Months')
    
    # Placement for source note
    ax.text(
        x=0.0, 
        y=-0.1,
        s='Source: Anycounty Police Dept. Incident Report Data, Anycounty DA Case Resolution Data', 
        transform=ax.transAxes,
        fontsize=9, 
        color='dimgray', 
        ha='left'
    )
    
    if i < len(category_order) - 1: 
        ax.set_xlabel('') 
    else:
        ax.set_xlabel('Filing Year', fontsize=12) 

plt.tight_layout()
plt.subplots_adjust(hspace=0.3) 

plt.savefig('Average Timeline Boxplot_ACDAO.png')
#---
# Frequency Table for Chosen Categories Case Status Outcomes
# Sources: Anycounty Police Dept. Incident Report Data, Anycounty DA Case Resolution Data,
#       & Anycounty DA Prosecution Data

filtered_pd_df['Incident Number'] = filtered_pd_df['Incident Number'].astype(str) # Standardize Incident Number

def create_percentage_table(df_source):
    """Generates the percentage distribution table for a given period."""
    
    df_source['Case Status'] = df_source['Case Status'].str.strip()
    
    # Create percentage table
    outcome_table_percentages = pd.crosstab(
        df_source['Major Category'],
        df_source['Case Status'],
        normalize='index' 
    ).mul(100).round(1)
    
    # Handle NaN
    if np.nan in outcome_table_percentages.columns:
        outcome_table_percentages = outcome_table_percentages.drop(columns=[np.nan])
    
    return outcome_table_percentages

# Apply extraction and cleaning
pattern = r'(\d{9})$'

prosecuted_cases_df['Incident Number'] = (
    prosecuted_cases_df['incident_number']
    .astype(str)
    .str.extract(pattern, expand=False)
)

prosecuted_cases_df.rename(columns={'case_status': 'Case Status'}, inplace=True)
prosecuted_cases_df['Case Status'] = prosecuted_cases_df['Case Status'].str.strip() # Clean whitespace
prosecuted_cases_df['Incident Number'] = prosecuted_cases_df['Incident Number'].astype(str) # Standardize key

merged_timeline_data = pd.merge(
    filtered_pd_df[['Incident Number', 'Major Category']].drop_duplicates(subset=['Incident Number']),
    resolution_df[['Incident Number', 'Filing Date', 'Disp Date']],
    on='Incident Number',
    how='inner'
)

# Merge Case Status onto the timeline data
merged_outcome_df = pd.merge(
    merged_timeline_data,
    prosecuted_cases_df[['Incident Number', 'Case Status']],
    on='Incident Number',
    how='inner'
)

# Cleaning and Preparation for Policy Analysis
merged_outcome_df.dropna(subset=['Case Status', 'Filing Date'], inplace=True)

# Extract Filing Year
merged_outcome_df['Filing Year'] = merged_outcome_df['Filing Date'].dt.year
    
# Define Policy Periods and Filter DFs
merged_outcome_df['Filing Year'] = pd.to_numeric(merged_outcome_df['Filing Year'], errors='coerce')
merged_outcome_df.dropna(subset=['Case Status', 'Filing Year'], inplace=True)

# Pre-Policy Data 2019 - 2024
pre_policy_df = merged_outcome_df[
    (merged_outcome_df['Filing Year'] >= 2019) & 
    (merged_outcome_df['Filing Year'] <= 2024)
].copy()

# Post-Policy Data 2025
post_policy_df = merged_outcome_df[
    merged_outcome_df['Filing Year'] == 2025
].copy()


# Export Final Tables

# Pre-Policy Table
pre_policy_table = create_percentage_table(pre_policy_df) 
pre_policy_table.to_csv('Case_Outcomes_Pre_Policy_2019-2024.csv')

# Post-Policy Table
post_policy_table = create_percentage_table(post_policy_df)
post_policy_table.to_csv('Case_Outcomes_Post_Policy_2025.csv')