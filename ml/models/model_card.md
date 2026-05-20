# Model Card: Adaptive Learning Cognitive Level Classifier

## Model Architecture
- Algorithm: [Your chosen algorithm, e.g., XGBoost]
- Task: Multi-class classification (4 classes)

## Training Data
- Source: Kaggle — Students Performance in Exams
- Size: ~700 samples (after SMOTE balancing)
- FCL Mapping: Low=1-4, Developing=5-7, Proficient=8-10, Advanced=11-T

## Performance Metrics (Test Set — evaluated once)
- Accuracy: [your value]
- Weighted F1: [your value]
- Per-class F1: Low=[x], Developing=[x], Proficient=[x], Advanced=[x]

## SHAP Top 5 Features
1. [feature name] — [educational interpretation]
2. ...

## Intended Use
- For: University of Eswatini secondary school pilot study
- Not for: High-stakes decisions without human oversight

## Limitations
- Trained on US Kaggle data; performance may vary for Eswatini students
- [Any fairness issues found in subgroup analysis]

## Ethical Considerations
- Cognitive level labels are predictions, not determinations
- Teachers retain final decision-making authority
