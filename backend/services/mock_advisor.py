"""Mock advisor that returns realistic demo responses without calling an LLM."""

from models.schemas import (
    AnalyzeResponse,
    DatasetProfile,
    ModelSuggestion,
    VizSuggestion,
)


def get_mock_recommendations(
    problem: str, profile: DatasetProfile
) -> AnalyzeResponse:
    numeric_cols = [c for c in profile.columns if c.dtype in ("integer", "float")]
    categorical_cols = [c for c in profile.columns if c.dtype == "categorical"]
    all_col_names = [c.name for c in profile.columns]
    num_col_names = [c.name for c in numeric_cols]

    # Pick likely target and feature columns for code snippets
    target = num_col_names[0] if num_col_names else all_col_names[-1]
    features = [c for c in all_col_names if c != target][:5]
    features_str = str(features)

    model_suggestions = [
        ModelSuggestion(
            name="Random Forest",
            model_type="classification" if len(numeric_cols) < len(categorical_cols) else "regression",
            reason=f"Works well with mixed feature types. Your dataset has {len(numeric_cols)} numeric and {len(categorical_cols)} categorical columns.",
            pros=[
                "Handles missing values and mixed types well",
                "Resistant to overfitting with proper tuning",
                "Provides feature importance rankings",
            ],
            cons=[
                "Can be slow on very large datasets",
                "Less interpretable than linear models",
            ],
            code=f'''import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

df = pd.read_csv("your_data.csv")

# Prepare features and target
features = {features_str}
target = "{target}"

X = pd.get_dummies(df[features], drop_first=True)
y = df[target]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
print(f"R² Score: {{r2_score(y_test, y_pred):.4f}}")
print(f"RMSE: {{mean_squared_error(y_test, y_pred, squared=False):.4f}}")
''',
        ),
        ModelSuggestion(
            name="Linear Regression",
            model_type="regression",
            reason=f"Good baseline model for {profile.row_count} rows. Simple, fast, and interpretable.",
            pros=[
                "Highly interpretable coefficients",
                "Fast training and prediction",
                "Good baseline to compare against",
            ],
            cons=[
                "Assumes linear relationships",
                "Sensitive to outliers and multicollinearity",
            ],
            code=f'''import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

df = pd.read_csv("your_data.csv")

features = {features_str}
target = "{target}"

X = pd.get_dummies(df[features], drop_first=True)
y = df[target]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = LinearRegression()
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
print(f"R² Score: {{r2_score(y_test, y_pred):.4f}}")
print(f"RMSE: {{mean_squared_error(y_test, y_pred, squared=False):.4f}}")

# Feature importance
for name, coef in sorted(zip(X_train.columns, model.coef_), key=lambda x: abs(x[1]), reverse=True):
    print(f"  {{name}}: {{coef:.4f}}")
''',
        ),
        ModelSuggestion(
            name="K-Means Clustering",
            model_type="clustering",
            reason="Useful for discovering natural groupings in the data before building predictive models.",
            pros=[
                "Unsupervised — no labels needed",
                "Fast and scalable",
                "Good for exploratory analysis",
            ],
            cons=[
                "Must choose K in advance",
                "Sensitive to feature scaling",
            ],
            code=f'''import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt

df = pd.read_csv("your_data.csv")

features = {features_str}
X = pd.get_dummies(df[features], drop_first=True)
X_scaled = StandardScaler().fit_transform(X)

# Find optimal K with elbow method
inertias = []
for k in range(2, 10):
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    km.fit(X_scaled)
    inertias.append(km.inertia_)

plt.plot(range(2, 10), inertias, marker="o")
plt.xlabel("Number of Clusters (K)")
plt.ylabel("Inertia")
plt.title("Elbow Method")
plt.show()
''',
        ),
    ]

    viz_suggestions = [
        VizSuggestion(
            chart_type="Correlation Heatmap",
            description=f"Shows relationships between numeric columns. Helps identify which features are most correlated with {target}.",
            code=f'''import pandas as pd
import plotly.express as px

df = pd.read_csv("your_data.csv")
numeric_df = df.select_dtypes(include="number")

fig = px.imshow(
    numeric_df.corr(),
    text_auto=".2f",
    color_continuous_scale="RdBu_r",
    title="Feature Correlation Heatmap",
)
fig.show()
''',
        ),
        VizSuggestion(
            chart_type="Distribution Plot",
            description=f"Shows the distribution of {target} to check for skewness and outliers.",
            code=f'''import pandas as pd
import plotly.express as px

df = pd.read_csv("your_data.csv")

fig = px.histogram(
    df, x="{target}", nbins=50, marginal="box",
    title="Distribution of {target}",
)
fig.show()
''',
        ),
        VizSuggestion(
            chart_type="Missing Values Bar Chart",
            description="Quickly see which columns have missing data and how much.",
            code=f'''import pandas as pd
import plotly.express as px

df = pd.read_csv("your_data.csv")
missing = (df.isnull().sum() / len(df) * 100).reset_index()
missing.columns = ["Column", "Missing %"]
missing = missing[missing["Missing %"] > 0].sort_values("Missing %", ascending=False)

fig = px.bar(missing, x="Column", y="Missing %", title="Missing Values by Column")
fig.show()
''',
        ),
    ]

    return AnalyzeResponse(
        dataset_profile=profile,
        model_suggestions=model_suggestions,
        viz_suggestions=viz_suggestions,
    )
