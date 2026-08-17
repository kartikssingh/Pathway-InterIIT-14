**Dataset**
1. AMLSim
2. SML-D

**Overview**
1. Supervised Learning: CatBoost classfier
2. Unsupervised Learning: Isolation Forest only on normal transactions
3. Bayesian Evidence: Rules Hits, Likelihood ratios, Bayesian
4. Fusion Model: Logistic Regression of 1, 2, 3.

**Preprocessing**
1. preprocessing/load_datasets.py
Loading Datasets, Normalizing the columns and unifing into one dataset.

**Featuring Engineering**
1. Producing features

**ML**
**Anomaly**
**Bayesian**
**Fusion**

**API Service**
**WatchDOg.py**
Monitors transaction CSV in real time , Recomputes incremental features, Calls API, Writes risk stream


**How to run**
```
python -m uvicorn service.api:app --reload --port 8000
```

```
python -m uvicorn service.llm:app --reload --port 9000
```

```
curl -X POST "http://127.0.0.1:9000/score_llm" \
  -H "Content-Type: application/json" \
  -d '{"features": { "total_amount_1h": 1200, "txn_count_1h": 3, "unique_cp_1h": 1, "avg_amount_1h": 400, "max_amount_1h": 900, "min_amount_1h": 100, "total_amount_24h": 4500, "txn_count_24h": 7, "unique_cp_24h": 4, "avg_amount_24h": 650, "max_amount_24h": 2000, "min_amount_24h": 50, "total_amount_7d": 15000, "txn_count_7d": 20, "unique_cp_7d": 5, "avg_amount_7d": 750, "max_amount_7d": 5000, "min_amount_7d": 50, "total_amount_30d": 42000, "txn_count_30d": 90, "unique_cp_30d": 15, "avg_amount_30d": 466, "max_amount_30d": 8000, "min_amount_30d": 20, "incoming_outgoing_ratio_7d": 1.2 }}'
```

```
LLM_URL
LLM_API
```

**Example**

```
curl -X POST "http://127.0.0.1:9000/score_llm" \
  -H "Content-Type: application/json" \
  -d '{"features": { "total_amount_1h": 1200, "txn_count_1h": 3, "unique_cp_1h": 1, "avg_amount_1h": 400, "max_amount_1h": 900, "min_amount_1h": 100, "total_amount_24h": 4500, "txn_count_24h": 7, "unique_cp_24h": 4, "avg_amount_24h": 650, "max_amount_24h": 2000, "min_amount_24h": 50, "total_amount_7d": 15000, "txn_count_7d": 20, "unique_cp_7d": 5, "avg_amount_7d": 750, "max_amount_7d": 5000, "min_amount_7d": 50, "total_amount_30d": 42000, "txn_count_30d": 90, "unique_cp_30d": 15, "avg_amount_30d": 466, "max_amount_30d": 8000, "min_amount_30d": 20, "incoming_outgoing_ratio_7d": 1.2 }}'
{"features":{"total_amount_1h":1200,"txn_count_1h":3,"unique_cp_1h":1,"avg_amount_1h":400,"max_amount_1h":900,"min_amount_1h":100,"total_amount_24h":4500,"txn_count_24h":7,"unique_cp_24h":4,"avg_amount_24h":650,"max_amount_24h":2000,"min_amount_24h":50,"total_amount_7d":15000,"txn_count_7d":20,"unique_cp_7d":5,"avg_amount_7d":750,"max_amount_7d":5000,"min_amount_7d":50,"total_amount_30d":42000,"txn_count_30d":90,"unique_cp_30d":15,"avg_amount_30d":466,"max_amount_30d":8000,"min_amount_30d":20,"incoming_outgoing_ratio_7d":1.2},"scores":{"p_ml":0.13579077625062422,"anomaly":0.8981771564659542,"evidence":0.003051095492096144,"rps":0.17422545502485534},"llm_explanation":{"risk_level":"MEDIUM","short_reason":"LLM returned non-JSON content, using fallback. Risk band MEDIUM.","long_reason":"Raw LLM content was: ```json\n{\n  \"risk_level\": \"high\",\n  \"short_reason\": \"High anomaly score and low evidence\",\n  \"long_reason\": \"The transaction features indicate a high level of suspicion due to the high anomaly score (0.898) and low evidence score (0.003). The transaction amount is unusually large compared to typical transactions, which suggests it may be an attempt at fraud.\",\n  \"recommended_action\": \"Review the transaction details for any unusual patterns or anomalies. Consider contacting the customer support team if you are unsure about the legitimacy of the transaction.\",\n  \"tags\": [\"fraud\", \"high-risk\"]\n}\n```","recommended_action":"Use raw scores and internal rules. Investigate if necessary.","tags":["llm_json_error","fallback"]}}

``` Using 1.5M Model(qwen)


**Synthetic Dataset**
1. synthetic_kyc.csv: Just random names, and places, but the user_id are linked to the unified transaction dataset created above
2. The user_id of the person and above can be matched.
3. Still can be flexible with column names.
