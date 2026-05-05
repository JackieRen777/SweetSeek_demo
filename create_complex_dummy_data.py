import pandas as pd
import os
import random

# Define the columns
columns = [
    'Compound Name', 'PubChem CID', 'MolecularFormula', 'MolecularWeight',
    'CanonicalSMILES', 'IsomericSMILES', 'InChI', 'InChIKey', 'IUPACName',
    'XLogP', 'TPSA', 'HBondDonorCount', 'HBondAcceptorCount',
    'RotatableBondCount', 'HeavyAtomCount', 'QED_Value', 'SA_Score',
    'Lipinski', 'Relative_Sweetness'
]

# Base list of sweeteners with key data (Name, CID, SMILES, Sweetness)
# Note: Sweetness is approximate relative to Sucrose=1.0
sweeteners = [
    # Sugars
    ('Sucrose', 5988, 'C12H22O11', 342.3, 'C(C1C(C(C(C(O1)OC2(C(C(C(O2)CO)O)O)CO)O)O)O)O', 1.0),
    ('Glucose', 5793, 'C6H12O6', 180.16, 'C(C1C(C(C(C(O1)O)O)O)O)O', 0.74),
    ('Fructose', 5984, 'C6H12O6', 180.16, 'C(C1C(C(C(O1)(CO)O)O)O)O', 1.73),
    ('Galactose', 6036, 'C6H12O6', 180.16, 'C(C1C(C(C(C(O1)O)O)O)O)O', 0.32),
    ('Maltose', 6255, 'C12H22O11', 342.3, 'C(C1C(C(C(C(O1)OC2C(C(C(C(O2)CO)O)O)O)O)O)O)O', 0.32),
    ('Lactose', 6134, 'C12H22O11', 342.3, 'C(C1C(C(C(C(O1)OC2C(C(C(O2)CO)O)O)O)O)O)O', 0.16),
    ('Trehalose', 7427, 'C12H22O11', 342.3, 'C(C1C(C(C(C(O1)OC2(C(C(C(O2)CO)O)O)CO)O)O)O)O', 0.45),
    ('Tagatose', 439324, 'C6H12O6', 180.16, 'C(C1C(C(C(O1)(CO)O)O)O)O', 0.92),
    
    # Sugar Alcohols
    ('Xylitol', 6912, 'C5H12O5', 152.15, 'C(C(C(C(CO)O)O)O)O', 1.0),
    ('Sorbitol', 5780, 'C6H14O6', 182.17, 'C(C(C(C(C(CO)O)O)O)O)O', 0.6),
    ('Mannitol', 6251, 'C6H14O6', 182.17, 'C(C(C(C(C(CO)O)O)O)O)O', 0.5),
    ('Erythritol', 222285, 'C4H10O4', 122.12, 'C(C(C(CO)O)O)O', 0.7),
    ('Maltitol', 493591, 'C12H24O11', 344.31, 'C(C1C(C(C(C(O1)OCC(C(C(C(CO)O)O)O)O)O)O)O)O', 0.9),
    ('Isomalt', 88735, 'C12H24O11', 344.31, 'C(C1C(C(C(C(O1)OCC(C(C(C(CO)O)O)O)O)O)O)O)O', 0.5),
    ('Lactitol', 15722, 'C12H24O11', 344.31, 'C(C1C(C(C(C(O1)OCC(C(C(C(CO)O)O)O)O)O)O)O)O', 0.4),
    
    # Artificial Sweeteners
    ('Aspartame', 134601, 'C14H18N2O5', 294.3, 'COC(=O)C(CC1=CC=CC=C1)NC(=O)C(CC(=O)O)N', 200.0),
    ('Saccharin', 5143, 'C7H5NO3S', 183.18, 'C1=CC=C2C(=C1)C(=O)NS2(=O)=O', 300.0),
    ('Sucralose', 71485, 'C12H19Cl3O8', 397.6, 'C(C1C(C(C(C(O1)OC2(C(C(C(O2)CCl)O)O)CCl)O)O)Cl)O', 600.0),
    ('Acesulfame K', 23689119, 'C4H4KNO4S', 201.24, 'CC1=CC(=O)[N-]S(=O)(=O)O1.[K+]', 200.0),
    ('Neotame', 9837248, 'C20H30N2O5', 378.5, 'CC(C)CC(C(=O)NC(CC1=CC=CC=C1)C(=O)OC)NC(CC(=O)O)C(=O)O', 8000.0),
    ('Advantame', 53394744, 'C24H30N2O7', 458.5, 'COC(=O)C(CC1=CC=CC=C1)NC(=O)C(CC(=O)O)NC(=O)C2=CC(=C(C=C2)O)OC', 20000.0),
    ('Cyclamate', 9257, 'C6H13NO3S', 179.24, 'C1CCCCC1NS(=O)(=O)O', 30.0),
    ('Alitame', 63018, 'C14H25N3O4S', 331.4, 'CC(C)(C)C(C(=O)O)NC(=O)C(C)NC(=O)C(CC(=O)O)N', 2000.0),
    ('Dulcin', 3196, 'C9H12N2O2', 180.20, 'CCOC1=CC=C(C=C1)NC(=O)N', 250.0),
    ('P-4000', 65094, 'C11H14N2O4', 238.24, 'CCOC1=CC=C(C=C1)N(=O)=O', 4000.0), # Warning: Toxic, but valid compound for DB
    ('Lugduname', 12345678, 'C26H29N3O6', 479.5, 'CN(CC(=O)O)C(=O)C(CC1=CC=CC=C1)NC(=O)C(C)NC(=O)C2=CC=C(C=C2)O', 225000.0), # Highest potency known
    
    # Natural High-Potency
    ('Stevioside', 442089, 'C38H60O18', 804.9, 'CC12CCCC(C1CCC34C2CCC(C3)(C(=C)C4)C(=O)OC5C(C(C(C(O5)CO)O)O)OC6C(C(C(C(O6)CO)O)O)O)OC7C(C(C(C(O7)CO)O)O)O', 250.0),
    ('Rebaudioside A', 6918840, 'C44H70O23', 967.0, 'CC12CCCC(C1CCC34C2CCC(C3)(C(=C)C4)C(=O)OC5C(C(C(C(O5)CO)O)O)OC6C(C(C(C(O6)CO)O)O)OC7C(C(C(C(O7)CO)O)O)O)OC8C(C(C(C(O8)CO)O)O)O', 240.0),
    ('Mogroside V', 9841865, 'C60H102O29', 1287.4, 'CC1(C(CCC2(C1CC(C3=C2C(CC4(C3(CCC(C4(C)C)OC5C(C(C(C(O5)CO)O)O)OC6C(C(C(C(O6)CO)O)O)O)C)C)O)C)C)OC7C(C(C(C(O7)CO)O)O)OC8C(C(C(C(O8)CO)O)O)OC9C(C(C(C(O9)CO)O)O)O)C', 300.0),
    ('Glycyrrhizin', 14982, 'C42H62O16', 822.9, 'CC1(C2CCC3(C(C2(CCC1OC4C(C(C(C(O4)C(=O)O)O)O)OC5C(C(C(C(O5)C(=O)O)O)O)O)C)C(=O)C=C6C3(CCC7(C6CC(CC7)(C)C(=O)O)C)C)C)C', 50.0),
    ('Thaumatin', 12345679, 'Protein', 22000, 'Protein_Structure_Placeholder', 2000.0), # Protein, special handling
    ('Monellin', 12345680, 'Protein', 11000, 'Protein_Structure_Placeholder', 1500.0),
    ('Brazzein', 12345681, 'Protein', 6500, 'Protein_Structure_Placeholder', 1000.0),
    ('Pentadin', 12345682, 'Protein', 12000, 'Protein_Structure_Placeholder', 500.0),
    ('Curculin', 12345683, 'Protein', 12500, 'Protein_Structure_Placeholder', 550.0),
    ('Miraculin', 12345684, 'Protein', 24600, 'Protein_Structure_Placeholder', 0.0), # Flavor modifier
    ('Osladin', 12345685, 'C26H42O7', 466.6, 'CC1C(C(C(C(O1)OC2C(C(C(C(O2)CO)O)O)O)O)O)OC3CC(CC4C3(CCC(C4(C)C)C)C)C', 500.0),
    ('Baiyunoside', 12345686, 'C32H50O12', 626.7, 'Diterpene_Glycoside_Placeholder', 500.0),
    ('Phyllodulcin', 119286, 'C16H14O5', 286.28, 'COC1=CC(=C(C=C1)O)C2CC3=C(C(=C(C=C3)O)O)C(=O)O2', 400.0),
    ('Hernandulcin', 126965, 'C15H24O2', 236.35, 'CC1=CCC(CC1=O)C(C)(C)O', 1000.0),
    ('Perillartine', 10886, 'C10H15NO', 165.23, 'CC1=CCC(CC1)C(=NO)C', 2000.0),
    
    # Rare Sugars / Others
    ('Allose', 93167, 'C6H12O6', 180.16, 'C(C1C(C(C(C(O1)O)O)O)O)O', 0.8),
    ('Altrose', 93168, 'C6H12O6', 180.16, 'C(C1C(C(C(C(O1)O)O)O)O)O', 0.8),
    ('Mannose', 18950, 'C6H12O6', 180.16, 'C(C1C(C(C(C(O1)O)O)O)O)O', 0.59),
    ('Sorbose', 94154, 'C6H12O6', 180.16, 'C(C1C(C(C(O1)(CO)O)O)O)O', 0.9),
    ('Xylose', 135191, 'C5H10O5', 150.13, 'C1C(C(C(C(O1)O)O)O)O', 0.4),
    ('Ribose', 5779, 'C5H10O5', 150.13, 'C1C(C(C(C(O1)O)O)O)O', 0.5),
    ('Arabinose', 66308, 'C5H10O5', 150.13, 'C1C(C(C(C(O1)O)O)O)O', 0.5),
    ('Lyxose', 93170, 'C5H10O5', 150.13, 'C1C(C(C(C(O1)O)O)O)O', 0.4),
    ('Rhamnose', 19233, 'C6H12O5', 164.16, 'CC1C(C(C(C(O1)O)O)O)O', 0.33),
    ('Fucose', 17106, 'C6H12O5', 164.16, 'CC1C(C(C(C(O1)O)O)O)O', 0.4),
    ('Kojibiose', 440658, 'C12H22O11', 342.3, 'C(C1C(C(C(C(O1)OC2C(C(C(C(O2)CO)O)O)O)O)O)O)O', 0.2),
    ('Nigerose', 440660, 'C12H22O11', 342.3, 'C(C1C(C(C(C(O1)OC2C(C(C(C(O2)CO)O)O)O)O)O)O)O', 0.3),
    ('Isomaltose', 440662, 'C12H22O11', 342.3, 'C(C1C(C(C(C(O1)OCC2C(C(C(C(O2)O)O)O)O)O)O)O)O', 0.5),
    ('Gentiobiose', 440664, 'C12H22O11', 342.3, 'C(C1C(C(C(C(O1)OCC2C(C(C(C(O2)O)O)O)O)O)O)O)O', 0.2),
    ('Melibiose', 440666, 'C12H22O11', 342.3, 'C(C1C(C(C(C(O1)OC2C(C(C(C(O2)O)O)O)O)O)O)O)O', 0.3),
]

data = []
for i, (name, cid, formula, mw, smiles, sweet) in enumerate(sweeteners):
    # Generate somewhat realistic dummy properties based on index
    logp = (i % 5) - 2.5 + (random.random() * 0.5)
    tpsa = 50 + (i % 10) * 15
    hbond_donor = (i % 6) + 1
    hbond_acceptor = (i % 8) + 2
    rotatable = (i % 5)
    heavy = (i % 20) + 10
    
    item = {
        'Compound Name': name,
        'PubChem CID': cid,
        'MolecularFormula': formula,
        'MolecularWeight': mw,
        'CanonicalSMILES': smiles,
        'IsomericSMILES': smiles, # Just duplicate for now
        'InChI': f'InChI=1S/{formula}/c{i+1}/h1H', # Dummy InChI
        'InChIKey': f'DUMMYKEY-{cid}-N',
        'IUPACName': f'{name} IUPAC Name Placeholder',
        'XLogP': round(logp, 2),
        'TPSA': round(tpsa, 1),
        'HBondDonorCount': hbond_donor,
        'HBondAcceptorCount': hbond_acceptor,
        'RotatableBondCount': rotatable,
        'HeavyAtomCount': heavy,
        'QED_Value': round(random.random(), 2),
        'SA_Score': round(1.0 + random.random() * 3, 1),
        'Lipinski': 1 if (mw <= 500 and logp <= 5 and hbond_donor <= 5 and hbond_acceptor <= 10) else 0,
        'Relative_Sweetness': sweet
    }
    data.append(item)

df = pd.DataFrame(data)

# Ensure data directory exists
os.makedirs('data', exist_ok=True)
os.makedirs('frontend-react/data', exist_ok=True) # Also save to frontend folder just in case

# Save to Excel
output_path = 'data/compounds_sweet.xlsx'
df.to_excel(output_path, index=False)
df.to_excel('frontend-react/data/compounds_sweet.xlsx', index=False)

print(f"Created {output_path} with {len(df)} compounds.")
print("Columns:", list(df.columns))
