%%
import pandas as pd
def serialize_if_dataframe(ret):
    if isinstance(ret, pd.DataFrame):
        # The 'orient="records"' parameter converts the DataFrame to a list of dictionaries
        # where each dictionary represents a row with column names as keys
        # This format is useful for JSON serialization of tabular data
        return ret.to_dict(orient="records")
    return ret

def serialize_ret(ret):
    """ Serialize the return value of a function to a dictionary. Valid types are: string, number, boolean, df. Lists and dicts are invalid. """
    valid_types = (str, int, float, bool, pd.DataFrame)
    if isinstance(ret, valid_types):
        return {"_ret": serialize_if_dataframe(ret)}
    elif isinstance(ret, (tuple, dict)):
        names = [f"_ret_{i}" for i in range(len(ret))] if isinstance(ret, tuple) else ret.keys()
        values = ret.values() if isinstance(ret, dict) else ret
        if not all(isinstance(item, valid_types) for item in values):
            print(f"Warning: Invalid return type in {names}: {values}")
            return None
        return {name: serialize_if_dataframe(item) for name, item in zip(names, values)}
    else:
        print(f"Warning: Invalid return type: {type(ret)}")
        return None

# Test cases for serialize_ret function
def test_serialize_ret():
    # Test with simple types
    assert serialize_ret("hello") == {"_ret": "hello"}
    assert serialize_ret(42) == {"_ret": 42}
    assert serialize_ret(3.14) == {"_ret": 3.14}
    assert serialize_ret(True) == {"_ret": True}
    
    # Test with pandas DataFrame
    df = pd.DataFrame({
        'Name': ['Alice', 'Bob'],
        'Age': [25, 30]
    })
    expected_df_result = {"_ret": [{'Name': 'Alice', 'Age': 25}, {'Name': 'Bob', 'Age': 30}]}
    assert serialize_ret(df) == expected_df_result
    
    # Test with tuple of valid types
    tuple_result = serialize_ret((42, "hello", True))
    assert tuple_result == {"_ret_0": 42, "_ret_1": "hello", "_ret_2": True}
    
    # Test with dictionary of valid types
    dict_result = serialize_ret({"num": 42, "text": "hello", "flag": True})
    assert dict_result == {"num": 42, "text": "hello", "flag": True}
    
    # Test with DataFrame in tuple and dict
    df_tuple_result = serialize_ret((df, "text"))
    assert df_tuple_result["_ret_0"] == expected_df_result["_ret"]
    assert df_tuple_result["_ret_1"] == "text"
    
    df_dict_result = serialize_ret({"data": df, "status": "success"})
    assert df_dict_result["data"] == expected_df_result["_ret"]
    assert df_dict_result["status"] == "success"
    
    # Test with invalid types
    assert serialize_ret([1, 2, 3]) is None  # List is invalid
    assert serialize_ret({"data": [1, 2, 3]}) is None  # Dict with list is invalid
    assert serialize_ret((1, [2, 3])) is None  # Tuple with list is invalid
    
    print("All serialize_ret tests passed!")

# Uncomment to run tests
test_serialize_ret()