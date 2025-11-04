# -*- coding: utf-8 -*-
import os
import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import datetime, date

# ───────────────────────────────
# CONFIGURATION
# ───────────────────────────────
st.set_page_config(page_title="Budget Mensuel", page_icon="💶", layout="wide")

FILE_FIXES = "depenses_fixes.csv"
FILE_VAR = "depenses_variables.csv"
FILE_TX = "transactions_variables.csv"
FILE_CONF = "config.csv"

DEFAULT_FIXES = pd.DataFrame({
    "Catégorie": [
        "Loyer", "Électricité", "Téléphone", "WiFi", "Assurance habitation",
        "Crédit téléphone", "ChatGPT+", "Netflix", "Apple Music",
        "Box", "Crédit EDF", "Salle de sport"
    ],
    "Budget fixé (€)": [306, 100, 18.5, 26.99, 8, 62.45, 22, 10.98, 5.99, 111, 50, 20],
    "Dépensé (€)": [0]*12
})

DEFAULT_VAR = pd.DataFrame({
    "Catégorie": ["Bouffe", "Gazoil"],
    "Budget fixé (€)": [200.0, 150.0],
    "Dépensé (€)": [0.0, 0.0]
})

DEFAULT_TX = pd.DataFrame(columns=["Datetime", "Catégorie", "Montant (€)", "Note"])
DEFAULT_CONF = pd.DataFrame({"cle": ["salaire"], "valeur": [2056.0]})

PALETTE = px.colors.qualitative.Set3 + px.colors.qualitative.Safe + px.colors.qualitative.Pastel

# ───────────────────────────────
# INITIALISATION
# ───────────────────────────────
def ensure_files():
    """Crée les fichiers CSV par défaut ou corrige leurs colonnes manquantes."""
    if not os.path.exists(FILE_FIXES):
        DEFAULT_FIXES.to_csv(FILE_FIXES, index=False)
    if not os.path.exists(FILE_VAR):
        DEFAULT_VAR.to_csv(FILE_VAR, index=False)
    if not os.path.exists(FILE_TX):
        DEFAULT_TX.to_csv(FILE_TX, index=False)
    if not os.path.exists(FILE_CONF):
        DEFAULT_CONF.to_csv(FILE_CONF, index=False)

    # Vérifie et corrige les colonnes manquantes
    def fix_columns(df, default_df, path):
        missing = [col for col in default_df.columns if col not in df.columns]
        if missing:
            for col in missing:
                df[col] = default_df[col].iloc[0]
            df = df[default_df.columns]
            df.to_csv(path, index=False)
        return df

    fixes = pd.read_csv(FILE_FIXES)
    var = pd.read_csv(FILE_VAR)
    tx = pd.read_csv(FILE_TX)
    conf = pd.read_csv(FILE_CONF)

    fixes = fix_columns(fixes, DEFAULT_FIXES, FILE_FIXES)
    var = fix_columns(var, DEFAULT_VAR, FILE_VAR)
    tx = fix_columns(tx, DEFAULT_TX, FILE_TX)
    conf = fix_columns(conf, DEFAULT_CONF, FILE_CONF)

ensure_files()

# ───────────────────────────────
# CHARGEMENT
# ───────────────────────────────
def load_all():
    return (
        pd.read_csv(FILE_FIXES),
        pd.read_csv(FILE_VAR),
        pd.read_csv(FILE_TX),
        pd.read_csv(FILE_CONF)
    )

fixes, var, tx, conf = load_all()

# ───────────────────────────────
# RECOMPUTE “Dépensé” variables
# ───────────────────────────────
def recompute_depenses_variables(var_df, tx_df):
    var_df = var_df.copy()
    var_df["Dépensé (€)"] = 0.0
    if not tx_df.empty:
        sums = tx_df.groupby("Catégorie")["Montant (€)"].sum()
        for cat, total in sums.items():
            if cat in var_df["Catégorie"].values:
                var_df.loc[var_df["Catégorie"] == cat, "Dépensé (€)"] = total
    return var_df

var = recompute_depenses_variables(var, tx)
var.to_csv(FILE_VAR, index=False)

# ───────────────────────────────
# SALAIRE & RÉSUMÉ GLOBAL
# ───────────────────────────────
salaire = float(conf.loc[conf["cle"] == "salaire", "valeur"].values[0])
st.title("💶 Tableau de bord budgétaire — propre et stable")

col1, col2, col3 = st.columns(3)
new_salaire = col1.number_input("Salaire mensuel (€)", min_value=0.0, value=salaire, step=10.0)
if new_salaire != salaire:
    conf.loc[conf["cle"] == "salaire", "valeur"] = new_salaire
    conf.to_csv(FILE_CONF, index=False)
    salaire = new_salaire

total_fixes = fixes["Dépensé (€)"].sum()
total_var = var["Dépensé (€)"].sum()
total_dep = total_fixes + total_var
reste = salaire - total_dep

col2.metric("Total dépenses", f"{total_dep:.2f} €")
col3.metric("Reste", f"{reste:.2f} €")

pie = pd.DataFrame({
    "Catégorie": ["Fixes", "Variables", "Reste"],
    "Montant (€)": [total_fixes, total_var, max(reste, 0)]
})
fig_global = px.pie(pie, values="Montant (€)", names="Catégorie",
                    color_discrete_sequence=["#F4A261", "#2A9D8F", "#90BE6D"],
                    hole=0.5)
fig_global.update_traces(textinfo="percent+label")
st.plotly_chart(fig_global, use_container_width=True)
st.markdown("---")

# ───────────────────────────────
# AJOUT CATÉGORIE / DÉPENSE
# ───────────────────────────────
st.subheader("🛍️ Dépenses variables")

colA, colB = st.columns(2)

with colA:
    new_cat = st.text_input("Nouvelle catégorie (ex. Maquillage)")
    new_budget = st.number_input("Budget (€)", min_value=0.0, step=5.0, key="budget_new")
    if st.button("Ajouter catégorie"):
        if new_cat.strip() and new_cat not in var["Catégorie"].values:
            var.loc[len(var)] = [new_cat.strip(), new_budget, 0.0]
            var.to_csv(FILE_VAR, index=False)
            st.success(f"Catégorie '{new_cat}' ajoutée ✅")
        else:
            st.warning("Catégorie vide ou déjà existante.")

with colB:
    cat_sel = st.selectbox("Catégorie", var["Catégorie"])
    montant = st.number_input("Montant dépensé (€)", min_value=0.0, step=1.0)
    note = st.text_input("Note (optionnel)")
    if st.button("Ajouter dépense"):
        if cat_sel and montant > 0:
            tx.loc[len(tx)] = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), cat_sel, montant, note]
            tx.to_csv(FILE_TX, index=False)
            var = recompute_depenses_variables(var, tx)
            var.to_csv(FILE_VAR, index=False)
            st.success(f"{montant:.2f} € ajouté à {cat_sel} ✅")
        else:
            st.warning("Saisie invalide.")

st.markdown("#### 🗂️ Historique de la catégorie sélectionnée")
hist = tx[tx["Catégorie"] == cat_sel].sort_values("Datetime", ascending=False)
if not hist.empty:
    st.dataframe(hist, use_container_width=True, height=200)
else:
    st.info("Aucune dépense enregistrée pour cette catégorie.")
st.markdown("---")

# ───────────────────────────────
# DIAGRAMMES VARIABLES
# ───────────────────────────────
st.markdown("### 🥧 Progression par catégorie (variables)")
if var.empty:
    st.info("Aucune catégorie variable disponible.")
else:
    cols = st.columns(min(len(var), 4))
    for i, row in enumerate(var.itertuples()):
        dep = float(row._3)
        budget = float(row._2)
        reste_cat = max(budget - dep, 0)
        fig = px.pie(
            names=["Dépensé", "Restant"],
            values=[dep, reste_cat],
            hole=0.6,
            color=["Dépensé", "Restant"],
            color_discrete_map={
                "Dépensé": PALETTE[i % len(PALETTE)],
                "Restant": "#E0E0E0"
            }
        )
        fig.update_traces(textinfo="percent+label")
        with cols[i % 4]:
            st.markdown(f"**{row.Catégorie}**")
            st.plotly_chart(fig, use_container_width=True)
            st.caption(f"{dep:.2f} € / {budget:.2f} € • Reste : {reste_cat:.2f} €")

st.markdown("---")

# ───────────────────────────────
# TABLEAU GLOBAL
# ───────────────────────────────
st.subheader("📋 Tableau global (éditable)")

fixes_df = fixes.copy()
fixes_df.insert(0, "Type", "Fixe")
var_df = var.copy()
var_df.insert(0, "Type", "Variable")

global_df = pd.concat([fixes_df, var_df], ignore_index=True)[
    ["Type", "Catégorie", "Budget fixé (€)", "Dépensé (€)"]
]

edited = st.data_editor(global_df, use_container_width=True, num_rows="dynamic")

if st.button("💾 Enregistrer modifications"):
    fixes_new = edited[edited["Type"] == "Fixe"].drop(columns=["Type"])
    vars_new = edited[edited["Type"] == "Variable"].drop(columns=["Type"])
    fixes_new.to_csv(FILE_FIXES, index=False)
    vars_new[["Catégorie", "Budget fixé (€)"]].to_csv(FILE_VAR, index=False)
    var = recompute_depenses_variables(vars_new, tx)
    var.to_csv(FILE_VAR, index=False)
    st.success("✅ Modifications enregistrées sans erreur !")

total_fixes = fixes_df["Dépensé (€)"].sum()
total_vars = var_df["Dépensé (€)"].sum()
st.caption(f"Totaux → Fixes : {total_fixes:.2f} € • Variables : {total_vars:.2f} € • Global : {total_fixes + total_vars:.2f} €")
