
# coding: utf-8

from io import StringIO
import requests
import json
import pandas as pd

universe_data = pd.read_csv('Universe Data.csv')
initial_portfolio = pd.read_csv('Initial Portfolio.csv')

try:
    from watson_developer_cloud import NaturalLanguageUnderstandingV1 as NLU
    from watson_developer_cloud.natural_language_understanding_v1 import Features, EntitiesOptions, KeywordsOptions, ConceptsOptions, CategoriesOptions, EmotionOptions, RelationsOptions, SemanticRolesOptions
except:
    get_ipython().system(u'pip install watson_developer_cloud')


optimization = {
    "portfolios": [],
    "objectives": [],
    "constraints": []
}


##### PUT IN YOUR HOLDINGS HERE #####
Holdings = []
Holdings.append({"asset":"CX_US0533321024_NYQ","quantity":14}) #Example of a holding
Holdings.append({"asset":"CX_US0584981064_NYQ","quantity":162})
Holdings.append({"asset":"CX_US1696561059_NYQ","quantity":67})
Holdings.append({"asset":"CX_US1912161007_NYQ","quantity":68})
Holdings.append({"asset":"CX_US29379VAY92_USD","quantity":67})
Holdings.append({"asset":"CX_US30231GAN25_USD","quantity":68})
Holdings.append({"asset":"CX_US46120E6023_NSQ","quantity":13})
Holdings.append({"asset":"CX_US4878361082_NYQ","quantity":67})
Holdings.append({"asset":"CX_US5486611073_NYQ","quantity":67})
Holdings.append({"asset":"CX_US56585AAG76_USD","quantity":67})
Holdings.append({"asset":"CX_US651639AN69_USD","quantity":67})
Holdings.append({"asset":"CX_US70450Y1038_NSQ","quantity":67})
Holdings.append({"asset":"CX_US9100471096_NYQ","quantity":67})


Cash = 0

tradeable_universe = {
    "name": "Universe",
    "type":"root",
    "holdings":[]
}
for index, row in universe_data.iterrows():
    holding = [h for h in Holdings if h["asset"] == row["Ticker"]]
    if holding:
        tradeable_universe["holdings"].append(holding[0])
    else:
        tradeable_universe["holdings"].append({"asset":row["Ticker"],"quantity":0})

optimization["portfolios"].append(tradeable_universe)

# ## Benchmark

#ENTER DETAILS HERE
Benchmark_name = "Aggressive"

#Assemble the benchmark portfolio using the above details:
Benchmark_col_name = "Benchmark - " + str(Benchmark_name)
benchmark = {
    "name": Benchmark_name,
    "type": "benchmark",
    "holdings": []
}
Benchmark_holdings = universe_data.filter(items=["Ticker","Last Close Price",Benchmark_col_name])[universe_data[Benchmark_col_name] != 0]
for index,row in Benchmark_holdings.iterrows():
    #Determine weight of each asset
    shares = row[Benchmark_col_name]
    holding = {"asset":row["Ticker"],"quantity":shares}
    benchmark["holdings"].append(holding)
    
optimization["portfolios"].append(benchmark)
'''
print("Benchmark debug")
print(benchmark)
'''

# ## Objective
optimization["objectives"] = [{
       "sense": "minimize",
       "measure": "variance",
       "attribute": "return",
       "portfolio": "Universe",
       "TargetPortfolio": Benchmark_name,
       "timestep": 30,
       "description": "minimize tracking error squared (variance of the difference between Universe portfolio and Benchmark returns) at time 30 days"
}]



# ## Preferences

##### CONSTRAINTS #####
Filtering_Constraints = []
Filtering_Constraints.append("Has Fossil Fuels")
ESG_Constraints = []
ESG_Constraints.append({"field":"Environmental","mean_score":"High"})
Allocation_Constraints = []
Allocation_Constraints.append({"field":"Sector","value":"Industrials","allocation":.3,"inequality":"less-or-equal"}) #Field values are..

#Result requirements
AllowShortSales = False           #No short-selling
MaximumInvestmentWeight = .2      #20%
#MaximumNumberofPositions = 5     #Cardinality constraint on the portfolio

#FILTERING CONTRAINTS
#Add subportfolio (how the optimization algorithm knows which asset has which property)
for f in Filtering_Constraints:
    subportfolio = {
        "ParentPortfolio":"Universe",
        "name":f,
        "type":"subportfolio",
        "holdings":[]
    }   
    #Find all the assets that meet the criteria and add them to the subportfolio. Populate holdings quantity if available.
    assets = universe_data.filter(items=["Ticker",f])[universe_data[f] != 0]
    for index,row in assets.iterrows():  
        holding = [h for h in Holdings if h["asset"] == row["Ticker"]]
        if holding:
            subportfolio["holdings"].append(holding[0])
        else:
            subportfolio["holdings"].append({"asset":row["Ticker"],"quantity":0})

    #Add subportfolio to list
    optimization["portfolios"].append(subportfolio)          
            
    #Add constraint to list
    optimization["constraints"].append({
        "attribute":"weight",
        "portfolio":f,
        "InPortfolio":"Universe",
        "relation":"equal",
        "constant":0.0,
        "description":"Excluding all securities which have the property " + f + "."
    })
    
#Debug

#ESG CONSTRAINTS
#Add subportfolio (how the optimization algorithm knows which asset has which property)
for e in ESG_Constraints:
    #initialize the subportfolio
    subportfolio = {
        "ParentPortfolio":"Universe",
        "name": e["mean_score"] + e["field"],
        "type":"subportfolio",
        "holdings":[]
    }
    
    #Find all the assets that meet the criteria and add them to the subportfolio. Populate holdings quantity if available.
    assets = universe_data.filter(items=["Ticker",e["field"]])[universe_data[e["field"]] == e["mean_score"]]
    for index,row in assets.iterrows():  
        holding = [h for h in Holdings if h["asset"] == row["Ticker"]]
        if holding:
            subportfolio["holdings"].append(holding[0])
        else:
            subportfolio["holdings"].append({"asset":row["Ticker"],"quantity":0})

    #Add subportfolio to list
    optimization["portfolios"].append(subportfolio)          
            
    #Add constraint to list
    optimization["constraints"].append({
        "attribute":"weight",
        "portfolio":e["mean_score"] + e["field"],
        "InPortfolio":"Universe",
        "relation":"greater-or-equal",
        "constant":.5,
        "description":"Creating an average " + e["field"] + " score of " + e["mean_score"] + "."
    })

#ALLOCATION CONSTRAINTS
#Add subportfolio (how the optimization algorithm knows which asset has which property)
for a in Allocation_Constraints:
    #initialize the subportfolio
    subportfolio = {
        "ParentPortfolio":"Universe",
        "name": a["value"],
        "type":"subportfolio",
        "holdings":[]
    }
    
    #Find all the assets that meet the criteria and add them to the subportfolio. Populate holdings quantity if available.
    assets = universe_data.filter(items=["Ticker",a["field"]])[universe_data[a["field"]] == a["value"]]
    for index,row in assets.iterrows():  
        holding = [h for h in Holdings if h["asset"] == row["Ticker"]]
        if holding:
            subportfolio["holdings"].append(holding[0])
        else:
            subportfolio["holdings"].append({"asset":row["Ticker"],"quantity":0})

    #Add subportfolio to list
    optimization["portfolios"].append(subportfolio)          
            
    #Add constraint to list
    optimization["constraints"].append({
        "attribute":"weight",
        "portfolio":a["value"],
        "InPortfolio":"Universe",
        "relation":a["inequality"],
        "constant":a["allocation"],
        "description":"Weight of " + a["value"] + " in the portfolio should be " + a["inequality"] + " to " + str(a["allocation"]) + "."
    })


#RESULT REQUIREMENTS

#No short-sale restriction
print ("The Portfolio result requirement:\t")
try:
    if AllowShortSales == False:
        optimization["constraints"].append({
           "attribute":"weight",
           "relation":"greater-or-equal",
           "members":"Universe",
           "constant":0,
           "description":"no short-sales for assets in Universe portfolio" 
        })
except:
    print("Short sales allowed")

#Maximum individual investment weight
try:
    optimization["constraints"].append({
       "attribute":"weight",
       "relation":"less-or-equal",
       "members":"Universe",
       "constant":MaximumInvestmentWeight,
       "description":"Weight of each asset from the Universe portfolio does not exceed " + str(MaximumInvestmentWeight*100) + "%."
    })
except:
    print("No maximum investment weight.")

#Maximum number of trades/positions
try:
    optimization["constraints"].append({
        "attribute": "count", 
        "relation": "less-or-equal", 
        "constant": MaximumNumberofPositions })
except:
    print("No maximum number of positions.")

#Minimum number of trades/positions
try:
    optimization["constraints"].append({
        "attribute": "count", 
        "relation": "greater-or-equal", 
        "constant": MinimumNumberofPositions })
except:
    print("No minimum number of positions.")

#Cash infusions
try:
    optimization["constraints"].append({
        "attribute:": "value",
        "portfolio": "Universe",
        "cashadjust": Cash,
        "description": "cash inflow of " + str(Cash) +" monetary units to the Universe portfolio"})
except:
    print("No cash infusions.")





r = open('r.json').read()
# # Step 5 - Viehe results of our optimization calculation:


new_portfolio = []
fields = ["Name","Last Close Price","One Month Return"]

#Gather fields
for f in Filtering_Constraints:
    fields.append(f)
for e in ESG_Constraints:
    fields.append(e["field"])
for a in Allocation_Constraints:
    fields.append(a["field"])
    
#Assemble the data frame
for i in json.loads(r)["Holdings"]:
    if i["OptimizedQuantity"] != 0:
        security_data = universe_data.filter(items=fields)[universe_data["Ticker"] == i["Asset"]]
        security_data = security_data.values.tolist()[0]
        security_data.append(i["OptimizedQuantity"] * security_data[1])
        total_data = (str(i["Asset"]),float(i["OptimizedQuantity"])) + tuple(security_data)
        new_portfolio.append(total_data)
        
fields = ["Ticker","Quantity"]+fields+["Total Value"]
    

OptimizedPortfolio = pd.DataFrame(new_portfolio, columns=fields)
print("\t")
print("The Initial Portfolio are as follows:\n")
print(initial_portfolio)
print("\t")
print("The Optimization Portfolio are as follows:\n")
print (OptimizedPortfolio)



# ## How close did we match the risk of the benchmark?
print("\t")
print("Tracking error between returns of the benchmark and the optimized portfolio is: \t%.2f%%" % 
      (100*(json.loads(r)["Metadata"]["ObjectiveValue"])**0.5))


# ## Checking that the constraints are met:

portfolio_value = 0
for j in new_portfolio:
    portfolio_value += j[-1]
print("\t")
print("Total Portfolio Value: \t%.2f" %portfolio_value)
print("\t")
#We use a pandas dataframe to do our aggregation analysis:
for f in fields[5:-1]:
    print("Total allocation to " + f+":")
    elements = set(OptimizedPortfolio[f])
    for e in elements:
        aggr = OptimizedPortfolio.filter(items=fields)[OptimizedPortfolio[f] == e]
        aggr_pct = aggr["Total Value"].sum() / portfolio_value
        print(str(e) + " \t\t" + str(round(aggr_pct,3)*100) + "%.")
    print("\t")


OptimizedPortfolio['Weight'] = OptimizedPortfolio.apply(lambda row: row['Quantity'] * row['Last Close Price'] / portfolio_value, axis=1)
OptimizedPortfolio
OptimizedPortfolio.groupby("Environmental")["Weight"].sum()
OptimizedPortfolio.groupby("Sector")["Weight"].sum()
OptimizedPortfolio.groupby("Has Fossil Fuels")["Weight"].sum()
OptimizedPortfolio['Return'] = OptimizedPortfolio.apply(lambda row: row['One Month Return'] * row['Weight'], axis=1)

print('\t')
print("Portfolio Return: %.5f%%" % (100*OptimizedPortfolio["Return"].sum()))
print("Annualized Portfolio Return: %.5f%%" % (100*12*OptimizedPortfolio["Return"].sum()))
print('\t')

import numpy as np


# Read covariance matrix
df_cov = pd.read_csv('Covar_Universe_Data.csv', sep=',', header=None)
cov_matr = df_cov.values
# Get holdings of initial and optimal portfolios as well as the benchmark portfolio
x_opt = []
x_init = []
for i in json.loads(r)["Holdings"]:
    x_opt.append(float(i["OptimizedQuantity"]))
    x_init.append(float(i["Quantity"]))
x_opt = np.array(x_opt)
x_init = np.array(x_init)
x_bench = universe_data[Benchmark_col_name].values

val = universe_data["Last Close Price"].values
ret = universe_data["One Month Return"].values

portf_init_val = np.dot(val.T, x_init) # Initial portfolio value
portf_init_val

portf_opt_val = np.dot(val.T, x_opt) # Optimal portfolio value
portf_opt_val

np.allclose(portf_opt_val, OptimizedPortfolio["Total Value"].sum()) # Sanity check

# Compute portfolio expected return, standard deviation and tracking error
w_opt   = x_opt * val / portf_opt_val
w_init  = x_init * val / portf_opt_val
w_bench = x_bench * val / portf_opt_val
ret_opt  = np.dot(ret.T, w_opt)
ret_init = np.dot(ret.T, w_init)
std_opt  = np.dot(np.dot(w_opt.T, cov_matr), w_opt)**0.5
std_init = np.dot(np.dot(w_init.T, cov_matr), w_init)**0.5
tr_err_opt  = np.dot(np.dot((w_opt-w_bench).T, cov_matr), (w_opt-w_bench))**0.5
tr_err_init = np.dot(np.dot((w_init-w_bench).T, cov_matr), (w_init-w_bench))**0.5

#data = [[round(100*ret_opt,3),round(100*ret_init,3)],[12*100*ret_opt,12*100*ret_init],[std_opt,std_init],[tr_err_opt,tr_err_init],[np.count_nonzero(w_opt),np.count_nonzero(w_init)]]
data = [[round(100*ret_opt,4),round(100*ret_init,4)],[round(12*100*ret_opt,4),round(12*100*ret_init,4)],[round(std_opt,4),round(std_init,4)],[round(tr_err_opt,4),round(tr_err_init,4)],[round(np.count_nonzero(w_opt),4),round(np.count_nonzero(w_init),4)]]
rows = ['Expected monthly return', 'Expected annual return','Standard deviation', 'Tracking error','Number of assets']
columns = ['optimal portfolio', 'initial portfolio']
df = pd.DataFrame(data, index=rows, columns=columns)
print (df)
print("\n")
#I assume that the interest rate of Canada is 1.5%
Interest_Rate= 0.015
print("The current interest rate of Canada is 1.5%")
if(12*100*ret_init < Interest_Rate):
    print("Your initial portfolio NPV < 0. \nTo avoid asset loss, you must adjust your porfolio.")
if(12*100*ret_opt < Interest_Rate):
    print("\nThe optimum portfolio NPV < 0 , \nTo avoid asset loss, you must adjust your investment choice") 


universe_data = pd.read_csv('Optimum Universe Data.csv')
environment_weight = [0.151509,
                          0.5,
                          0.348491]
sector_weight = [21698.09891,
                     37782.22557,
                     15457.12856,
                     12671.85712,
                     10937.8196,
                     1462.290235]

initial_name_weight = list(universe_data.get('Total Value'))
name_weight = list(initial_portfolio.get('Total Value'))


with open('environment_weight.json', 'w', encoding='utf-8') as f:
    f.write(json.dumps(environment_weight, indent=2))
    f.flush()
with open('sector_weight', 'w', encoding='utf-8') as f:
    f.write(json.dumps(sector_weight, indent=2))
    f.flush()
with open('initial_name_weight.json', 'w', encoding='utf-8') as f:
    f.write(json.dumps(initial_name_weight, indent=2))
with open('name_weight.json', 'w', encoding='utf-8') as f:
    f.write(json.dumps(name_weight, indent=2))
    f.flush()

print("\t")
print("json file has been created")
print("\t")
print("Please use Microsoft Edge broswer to open.")
print("↓ ↓ ↓")
print("click_me_run.html")
print("↑ ↑ ↑")
print("To see our visualization product")
print("\t")
print("If you use Mac or you't have Microsoft Edge. Don't worry.")
print("I have deployed it on my cloud web server, just click the URL below with your PC/phone/pad.")
print("\t")
print("↓ ↓ ↓")
print("http://hxy0714.xin/visualization.html")
print("↑ ↑ ↑")
