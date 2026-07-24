import pandas as pd
import numpy as np

def make_xlsx_file(filename, lists):
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        for list_name, list_dataframe in lists.items():
            list_dataframe.to_excel(writer, sheet_name=list_name, index=False)    
    

PERIOD = 6
bills_path = 'bills txt.txt'
rates_path = 'rates txt.txt'
classifier_path = 'Классификатор.xlsx'


bills_df = pd.read_csv(bills_path)
bills_df['date'] = pd.to_datetime(bills_df['date'])

rates_df = pd.read_csv(rates_path)
rates_df['month'] = pd.to_datetime(rates_df['month'])

classifier_df = pd.read_excel(classifier_path)
classifier_df.head()

currency_df = pd.merge(bills_df, rates_df, left_on=[bills_df['date'].dt.month, 'currency'], right_on=[rates_df['month'].dt.month, 'currency'], how='left')
currency_df['rate_to_EUR'].fillna(1)
currency_df['rate_to_EUR'] = currency_df['rate_to_EUR'].fillna(1)
currency_df['EUR_amount'] = currency_df['amount'] * currency_df['rate_to_EUR']  
currency_df = currency_df[['bill_id', 'date', 'vendor', 'project', 'category_code', 'currency', 'amount', 'description', 'EUR_amount']]

period_mask = currency_df['date'].dt.month == PERIOD
period_project_df = currency_df[period_mask]

classified_mask = period_project_df['category_code'].isin(classifier_df['category_code'])
classified_period_project_df = period_project_df[classified_mask]

reports = {}

project_code_amount_df = classified_period_project_df.groupby(['project', 'category_code'])['EUR_amount'].sum().reset_index()

reports['report'] = project_code_amount_df

make_xlsx_file('report.xlsx', reports)

lists = {}

# пустой проект
lists['Without_a_project'] = currency_df[currency_df['project'].isna()]

# дубликаты
lists['Duplicates'] = currency_df[currency_df.duplicated()]

# отрицательные суммы
lists['Amount_less_zero'] = currency_df[currency_df['EUR_amount'] < 0]

# Категория вне классификации
lists['Unclassified_category'] = period_project_df[~classified_mask]

# Вне периода
lists['Outside_period'] = currency_df[~period_mask]

make_xlsx_file('control_file.xlsx', lists)

# Вычисляем сумму с заполнением
sum_report_and_unclassified = project_code_amount_df.groupby('project')['EUR_amount'].sum().add(lists['Unclassified_category'].groupby('project')['EUR_amount'].sum(), fill_value=0)
first = period_project_df.groupby('project')['EUR_amount'].sum()
# Маска: True, где значения близки
mask = np.isclose(first, sum_report_and_unclassified)

if mask.all():
    print("Сверка совпала – все значения равны (с учётом погрешности).")
else:
    # Индексы, где есть расхождение
    diff_idx = first.index[~mask]
    print("Обнаружены расхождения в следующих проектах:")
    for idx in diff_idx:
        print(f"  {idx}: Первичный = {first[idx]}, отчет + неклассифицированные = {sum_report_and_unclassified[idx]}")