import pandas as pd
import os

# Sample data for sweet compounds
data = {
    'id': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    'name': [
        'Sucrose', 'Fructose', 'Glucose', 'Aspartame', 'Saccharin', 
        'Sucralose', 'Stevioside', 'Rebaudioside A', 'Acesulfame K', 'Neotame'
    ],
    'common_name': [
        'Table Sugar', 'Fruit Sugar', 'Grape Sugar', 'NutraSweet', 'Sweet\'N Low',
        'Splenda', 'Stevia', 'Reb A', 'Sunett', 'Newtame'
    ],
    'sweetness_potency': [
        1.0, 1.7, 0.74, 200, 300, 
        600, 250, 300, 200, 8000
    ],
    'molecular_formula': [
        'C12H22O11', 'C6H12O6', 'C6H12O6', 'C14H18N2O5', 'C7H5NO3S',
        'C12H19Cl3O8', 'C38H60O18', 'C44H70O23', 'C4H4KNO4S', 'C20H30N2O5'
    ],
    'cas_number': [
        '57-50-1', '57-48-7', '50-99-7', '22839-47-0', '81-07-2',
        '56038-13-2', '57817-89-7', '58543-16-1', '55589-62-3', '165450-17-9'
    ],
    'description': [
        'Common table sugar, a disaccharide composed of glucose and fructose.',
        'A ketonic simple sugar found in many plants.',
        'A simple sugar that is an important energy source in living organisms.',
        'An artificial non-saccharide sweetener used as a sugar substitute.',
        'An artificial sweetener with effectively no food energy.',
        'A zero-calorie artificial sweetener.',
        'A glycoside derived from the stevia plant.',
        'A steviol glycoside that is 240 times sweeter than sugar.',
        'A calorie-free sugar substitute.',
        'An artificial sweetener that is between 7,000 and 13,000 times sweeter than sucrose.'
    ]
}

df = pd.DataFrame(data)

# Ensure the data directory exists
os.makedirs('data', exist_ok=True)

# Save to Excel
output_path = 'data/compounds.xlsx'
df.to_excel(output_path, index=False)

print(f"Created dummy Excel file at {output_path}")
