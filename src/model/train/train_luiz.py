# Databricks notebook source
# MAGIC  %pip install feature-engine==1.4.1 scikit-plot

# COMMAND ----------

from sklearn import model_selection
from sklearn import pipeline
from sklearn import tree
from sklearn import ensemble
from sklearn import metrics

from feature_engine import imputation
from feature_engine import encoding

import pandas as pd

import scikitplot as skplt

import mlflow

# COMMAND ----------

# DBTITLE 1,Sample
df = spark.table("silver_gc.abt_model_churn")

df_oot = df.filter(df.dtRef == '2022-01-11').toPandas()
df_train = df.filter(df.dtRef < '2022-01-11').toPandas()

columns = df_train.columns

target = 'flNaoChurn'
ids = ['dtRef', 'idPlayer']
to_remove = ['flAssinatura']

features = list(set(columns) - set([target]) - set(ids) - set(to_remove))

x_train, x_test, y_train, y_test = model_selection.train_test_split(df_train[features],
                                                                    df_train[target],
                                                                    test_size=0.2,
                                                                    random_state=42)
print("Taxa de resposta treino:", 100*y_train.mean().round(4), "%")
print("Taxa de resposta treino:", 100*y_test.mean().round(4), "%")

# COMMAND ----------

# DBTITLE 1,Explore
# Identificando Missings

missing_columns = x_train.count() [x_train.count() < x_train.shape[0]].index.tolist()

missing_columns.sort()
missing_columns

missing_flag = [
     'avg1Kill',
     'avg2Kill',
     'avg3Kill',
     'avg4Kill',
     'avg5Kill',
     'avgAssist',
     'avgBombeDefuse',
     'avgBombePlant',
     'avgClutchWon',
     'avgDamage',
     'avgDeath',
     'avgFirstKill',
     'avgFlashAssist',
     'avgHits',
     'avgHs',
     'avgHsRate',
     'avgKDA',
     'avgKDR',
     'avgKill',
     'avgLastAlive',
     'avgPlusKill',
     'avgRoundsPlayed',
     'avgShots',
     'avgSurvived',
     'avgTk',
     'avgTkAssist',
     'avgTrade',
     'qtRecencia',
     'vlHsHate',
     'vlKDA',
     'vlKDR',
     'vlLevel',
     'winRate',
    ]

missing_zero = [
     'propAncient',
     'propDia01',
     'propDia02',
     'propDia03',
     'propDia04',
     'propDia05',
     'propDia06',
     'propDia07',
     'propDust2',
     'propInferno',
     'propMirage',
     'propNuke',
     'propOverpass',
     'propTrain',
     'propVertigo',
     'qtDias',
     'qtPartidas',
    ]

cat_features = x_train.dtypes[x_train.dtypes == 'object'].index.tolist()

# COMMAND ----------

x_train.describe()

# COMMAND ----------

# DBTITLE 1,Modify
fe_missing_flag = imputation.ArbitraryNumberImputer(arbitrary_number=-100,
                                                    variables=missing_flag,
                                                    )
fe_missing_zero = imputation.ArbitraryNumberImputer(arbitrary_number=0,
                                                    variables=missing_zero,
                                                    )

fe_onehot = encoding.OneHotEncoder(variables=cat_features)

# COMMAND ----------

# DBTITLE 1,Modeling
model = ensemble.AdaBoostClassifier(n_estimators = 250, learning_rate = 0.85, random_state = 42)

model_pipeline = pipeline.Pipeline( [ ("Missing Flag", fe_missing_flag),
                                      ("Missing Zero", fe_missing_zero),
                                      ("OneHot", fe_onehot),
                                      ("Classificador", model)] )

# COMMAND ----------

mlflow.set_experiment("/Users/luizpedro6@gmail.com/ex-churn-luiz")

with mlflow.start_run():
    
    metrics_dct = {}

    mlflow.sklearn.autolog()
    
    print("Treinando o modelo...")
    model_pipeline.fit(x_train, y_train)
    print("Modelo Treinado!")
    
    y_train_predict = model_pipeline.predict(x_train)
    y_train_proba = model_pipeline.predict_proba(x_train)
    metrics_dct["acc_train"] = metrics.accuracy_score(y_train, y_train_predict)
    metrics_dct["auc_train"] = metrics.roc_auc_score(y_train, y_train_proba[:,1])
    
    y_test_predict = model_pipeline.predict(x_test)
    y_test_proba = model_pipeline.predict_proba(x_test)
    metrics_dct["acc_test"] = metrics.accuracy_score(y_test, y_test_predict)
    metrics_dct["auc_test"] = metrics.roc_auc_score(y_test, y_test_proba[:,1])
    
    y_oot_predict = model_pipeline.predict(df_oot[features])
    y_oot_proba = model_pipeline.predict_proba(df_oot[features])
    metrics_dct["acc_oot"] = metrics.accuracy_score(df_oot[target], y_oot_predict)
    metrics_dct["auc_oot"] = metrics.roc_auc_score(df_oot[target], y_oot_proba[:,1])
    
    mlflow.log_metrics(metrics_dct)

# COMMAND ----------

y_test_predict = model_pipeline.predict(x_test)
y_probas = model_pipeline.predict_proba(x_test)

acc_test = metrics.accuracy_score(y_test, y_test_predict)

print("Acurácia teste:", acc_test)

# COMMAND ----------

# DBTITLE 1,Feature Importance
features_fit = model_pipeline[:-1].transform(x_train).columns.tolist()

features_importance = pd.Series(model.feature_importances_, index=features_fit)
features_importance.sort_values(ascending=False).head(15)

# COMMAND ----------

skplt.metrics.plot_roc(y_test, y_probas)

# COMMAND ----------

skplt.metrics.plot_ks_statistic(y_test, y_probas)

# COMMAND ----------

skplt.metrics.plot_cumulative_gain(y_test, y_probas)

# COMMAND ----------

skplt.metrics.plot_lift_curve(y_test, y_probas)

# COMMAND ----------

y_probas_oot = grid_model.predict_proba(df_oot[features])

skplt.metrics.plot_roc(df_oot[target], y_probas_oot)

skplt.metrics.plot_ks_statistic(df_oot[target], y_probas_oot)

skplt.metrics.plot_lift_curve(df_oot[target], y_probas_oot)

# COMMAND ----------

df_probas = pd.DataFrame(
        {"probas": y_probas[:,0],
         "target": y_test})
df_probas = df_probas.sort_values(by="probas", ascending=False)
1-df_probas.head(int(df_probas.shape[0] * 0.2))["target"].mean()
