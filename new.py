import pandas as pd

@mock_inputs
def mock_get_user_inputs():
    """Returns mock inputs with a default year of 2024 and a state of Colorado."""
    return {
        'year': 2024,
        'state': 'Colorado', 
        'bills': [
            {'bill_id': '1025', 'endorse': False, 'sponsor_name': 'Johnson, Emily'},
            {'bill_id': '1026', 'endorse': True, 'sponsor_name': 'Williams, Michael'}
        ]
    }

@mock
def fetch_legiscan_data(state, bill):
    """Fetch LegiScan data for the specified state and bill."""
    return pd.DataFrame({
        'Legislator': ['Johnson, Emily', 'Williams, Michael'],
        'Roll Call': [1, 0],
        'Party': ['Democrat', 'Republican']
    })

@mock
def fetch_acu_scores(legislators):
    """Fetch ACU scores for a list of legislators."""
    return pd.DataFrame({
        'Legislator': ['Johnson, Emily', 'Williams, Michael'],
        'Score': [95, 100]  # Increased scores by 10
    })

@mock
def combine_data(legiscan_df, acu_df):
    """Combine LegiScan and ACU data into a single DataFrame."""
    return pd.merge(legiscan_df, acu_df, on='Legislator')

def main():
    """Main workflow for processing legislative data."""
    user_inputs = mock_get_user_inputs()
    combined_data = pd.DataFrame()
    for bill in user_inputs['bills']:
        legiscan_df = fetch_legiscan_data(user_inputs['state'], bill['bill_id'])
        acu_df = fetch_acu_scores(legiscan_df['Legislator'])
        combined_data = pd.concat([combined_data, combine_data(legiscan_df, acu_df)], ignore_index=True)
    combined_data['Year'] = user_inputs['year']
    combined_data['State'] = user_inputs['state']
    combined_data = combined_data[['Year', 'State'] + [col for col in combined_data.columns if col not in ['Year', 'State']]]
    print(combined_data)
    print("Success")

if __name__ == "__main__":
    main()
