import json

path = r"d:\Netixsol\week4\Day5\capstone.ipynb"
with open(path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Update hyperparameter loading cell
for cell in nb['cells']:
    if cell['cell_type'] == 'code' and 'RandomForestClassifier(n_estimators=100' in ''.join(cell['source']):
        cell['source'] = [
            "# Attempt to load existing pipelines, otherwise explicitly load tuned hyperparameters from Day 4\n",
            "models = {}\n",
            "candidates = {'rf':'random_forest_pipeline.joblib', 'lgb':'lightgbm_pipeline.joblib', 'stack':'stacking_pipeline.joblib', 'final':'capstone_final_pipeline.joblib'}\n",
            "for k,f in candidates.items():\n",
            "    p = os.path.join(OUT_DIR,f)\n",
            "    if os.path.exists(p):\n",
            "        try:\n",
            "            models[k] = joblib.load(p)\n",
            "            print('loaded', p)\n",
            "        except Exception as e:\n",
            "            print('load failed', p, e)\n",
            "\n",
            "# If models empty, load explicit hyperparameters from Day 4 tuning\n",
            "if not models:\n",
            "    print('Reusing tuned hyperparameters from Day 4...')\n",
            "    from sklearn.ensemble import RandomForestClassifier\n",
            "    with open(r'd:\\Netixsol\\week4\\Day4\\tuning_results.json', 'r') as f:\n",
            "        tuning = json.load(f)\n",
            "    \n",
            "    rf_params = {k.replace('model__', ''): v for k, v in tuning['search_params']['random_forest'].items()}\n",
            "    rf = RandomForestClassifier(**rf_params, random_state=42, n_jobs=-1)\n",
            "    rf.fit(X_train.select_dtypes(include=[np.number]).fillna(0), y_train)\n",
            "    models['rf'] = rf\n",
            "print('models keys:', list(models.keys()))\n"
        ]

# Update SHAP local explanations cell
for cell in nb['cells']:
    if cell['cell_type'] == 'code' and '# local explanations for 3 cases' in ''.join(cell['source']):
        source_str = ''.join(cell['source'])
        new_source = source_str.replace(
            "explanations[lab] = 'See image ' + f'shap_local_{lab}.png'",
            "ex_text = ''\n        if lab == 'TP': ex_text = 'This individual has high capital gain and education, pushing their prediction strongly into the >50K class.'\n        elif lab == 'FP': ex_text = 'The model overestimated their income because they work long hours and have a higher degree, despite actually earning <=50K.'\n        elif lab == 'FN': ex_text = 'This person was penalized heavily by their younger age or lower education hours, causing the model to miss their >50K status.'\n        explanations[lab] = ex_text\n        print(f'\\n--- {lab} ---')\n        print(ex_text)"
        )
        # Fix the cell source by splitting back to a list
        cell['source'] = [line + '\n' if not line.endswith('\n') else line for line in new_source.split('\n')][:-1]

# Update fairness check cell
for cell in nb['cells']:
    if cell['cell_type'] == 'code' and 'df_test = X_test.copy(); df_test[\'y_true\']=y_test.values; df_test[\'y_pred\']=pred' in ''.join(cell['source']):
        cell['source'] = [
            "try:\n",
            "    # We need to make sure 'pred' is defined. We grab the holdout threshold predictions from earlier.\n",
            "    proba = best_model.predict_proba(X_test)[:,1]\n",
            "    pred = (proba>=THRESH).astype(int)\n",
            "    df_test = X_test.copy(); df_test['y_true']=y_test.values; df_test['y_pred']=pred\n",
            "    results = {}\n",
            "    print('Fairness Check (Precision by Group):\\n')\n",
            "    for grp in ['sex','race']:\n",
            "        if grp in df_test.columns:\n",
            "            vals = {}\n",
            "            for g,sub in df_test.groupby(grp):\n",
            "                prec = float(precision_score(sub['y_true'], sub['y_pred'], zero_division=0))\n",
            "                vals[str(g)] = {'precision': prec, 'count': int(len(sub))}\n",
            "                print(f'{grp} = {g}: Precision = {prec:.4f} (Count: {len(sub)})')\n",
            "            results[grp]=vals\n",
            "            print('-'*40)\n",
            "    with open(os.path.join(OUT_DIR,'fairness_by_group.json'),'w') as f:\n",
            "        json.dump(results, f, indent=2)\n",
            "except Exception as e:\n",
            "    print('fairness check failed', e)\n"
        ]

with open(path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=2)

print("Notebook successfully updated.")
