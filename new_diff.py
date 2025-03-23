import Pandas as Pd

@MockInputs
def MockGetUserInputs():
    """Returns mock inputs with a default year of 2024 and a state of Colorado."""
    return {
        'Year': 2024,
        'State': 'Colorado', 
        'Bills': [
            {'BillId': '1025', 'Endorse': False, 'SponsorName': 'Johnson, Emily'},
            {'BillId': '1026', 'Endorse': True, 'SponsorName': 'Williams, Michael'}
        ]
    }

@Mock
def FetchLegiScanData(State, Bill):
    """Fetch LegiScan data for the specified state and bill."""
    return Pd.DataFrame({
        'Legislator': ['Johnson, Emily', 'Williams, Michael'],
        'RollCall': [1, 0],
        'Party': ['Democrat', 'Republican']
    })

@Mock
def FetchACUScores(Legislators):
    """Fetch ACU scores for a list of legislators."""
    return Pd.DataFrame({
        'Legislator': ['Johnson, Emily', 'Williams, Michael'],
        'Score': [85, 90]
    })

@Mock
def CombineData(LegiScanDf, AcuDf):
    """Combine LegiScan and ACU data into a single DataFrame."""
    return Pd.merge(LegiScanDf, AcuDf, on='Legislator')

def Main():
    """Main workflow for processing legislative data."""
    UserInputs = MockGetUserInputs()
    CombinedData = Pd.DataFrame()
    for Bill in UserInputs['Bills']:
        LegiScanDf = FetchLegiScanData(UserInputs['State'], Bill['BillId'])
        AcuDf = FetchACUScores(LegiScanDf['Legislator'])
        CombinedData = Pd.concat([CombinedData, CombineData(LegiScanDf, AcuDf)], ignore_index=True)
    CombinedData['Year'] = UserInputs['Year']
    CombinedData['State'] = UserInputs['State']
    CombinedData = CombinedData[['Year', 'State'] + [Col for Col in CombinedData.columns if Col not in ['Year', 'State']]]
    print(CombinedData)
    print("Success")

if __name__ == "__main__":
    Main()

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
        'Score': [85, 90]
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