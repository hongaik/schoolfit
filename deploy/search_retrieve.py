import pandas as pd
import numpy as np
import ast
import pickle
from pathlib import Path
ROOT = Path(__file__).resolve().parent
from sentence_transformers import SentenceTransformer
from sentence_transformers import util

@st.cache_resource
def load_model():
    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

model = load_model()

full_records = ROOT / 'data' / 'full_records.csv'
cca_vectors = ROOT / 'artifacts' / 'cca_vectors.npy'
cca_names = ROOT / 'artifacts' / 'cca_names.pkl'
alp_llp_vectors = ROOT / 'artifacts' / 'alp_llp_vectors.npy'
alp_llp_names = ROOT / 'artifacts' / 'alp_llp_domains.pkl'

data = pd.read_csv(full_records)

cca_embeddings = np.load(cca_vectors)
with open(cca_names,'rb') as f:
    cca_names = pickle.load(f)

prog_embeddings = np.load(alp_llp_vectors)
with open(alp_llp_names,'rb') as f:
    prog_names = pickle.load(f)

# ========================= CCA =========================     

cca_cols = ['physical_sports', 'visual_and_performing_arts', 'uniformed_groups', 'clubs_and_societies']

# Convert string arrays to literal arrays
for col in cca_cols:
    data[col] = data[col].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)

cca_set = set()

for row in data.itertuples():
    for sports in row.physical_sports:
        cca_set.add(sports)
    for arts in row.visual_and_performing_arts:
        cca_set.add(arts)
    for ug in row.uniformed_groups:
        cca_set.add(ug)
    for cns in row.clubs_and_societies:
        cca_set.add(cns)
        
cca_list = sorted(list(cca_set))

niche_prog_list = set()

for row in data.itertuples():
    niche_prog_list.add(row.alp_domain)
    niche_prog_list.add(row.llp_domain)
        
niche_prog_list = sorted([i.upper() for i in list(niche_prog_list) if i.upper() != 'GENERAL HOLISTIC DEVELOPMENT'])

def get_best_cca_match(user_query):
    # Create vector for user_query
    query_vec = model.encode(user_query)

    # Perform cosine similarity between query vector & each embedding vector - returns array [[scores query 1],[scores query 2]]
    scores = util.cos_sim(query_vec, cca_embeddings)[0]
    # Obtain index for best score
    best_idx = np.argmax(scores)

    # matches with 0.3 (can be adjusted) of top score are considered 
    top_matches = sorted([(cca_names[i],scores[i].item()) for i, score in enumerate(scores) if score > scores[best_idx].item()*0.3], key=lambda x: x[1], reverse=True)
    top_matches_dict = dict(top_matches)
    
    # Normalisation
    max_score = max(top_matches_dict.values())
    top_matches_dict = {tm: score/max_score for tm,score in top_matches_dict.items()}
    
    return top_matches_dict

# Obtain list of tuples (CCA, scores) 
def cca_similarity(inputs=[]):
    aggregated_matches = {}
    for i in inputs:
        top_matches = get_best_cca_match(i)
        # top_matches for first input takes the match 
        if not aggregated_matches:
            aggregated_matches = top_matches
        # For subsequent inputs, any matches are checked against the aggregated list
        else: 
            for tm, score in top_matches.items():
                # If the match does not exist in aggregated list (i.e. new) add new entry
                if tm not in aggregated_matches:
                    aggregated_matches[tm] = score
                # If the match already exist in aggregated list, sum up the scores
                else: 
                    current = aggregated_matches[tm]
                    aggregated_matches[tm] = current+score
    # Normalisation
    max_score = max(aggregated_matches.values())
    aggregated_matches = {tm: score/max_score for tm,score in aggregated_matches.items()}
    
    sorted_matches = sorted(aggregated_matches.items(), key=lambda item:item[1], reverse=True)
    return sorted_matches

# ========================= PROG =========================     
def get_best_prog_match(user_query):

    # Create vector for user_query
    query_vec = model.encode(user_query)

    # Perform cosine similarity between query vector & each embedding vector - returns array [[scores query 1],[scores query 2]]
    scores = util.cos_sim(query_vec, prog_embeddings)[0]
    # Obtain index for best score
    best_idx = np.argmax(scores)

    top_matches = sorted([(prog_names[i],scores[i].item()) for i, score in enumerate(scores) if score > scores[best_idx].item()*0.5], key=lambda x: x[1], reverse=True)
    top_matches_dict = dict(top_matches)
    
    # Normalisation
    max_score = max(top_matches_dict.values())
    top_matches_dict = {tm: score/max_score for tm,score in top_matches_dict.items()}
    
    return top_matches_dict

def prog_similarity(inputs=[]):
    aggregated_matches = {}
    for i in inputs:
        top_matches = get_best_prog_match(i)
        if not aggregated_matches:
            aggregated_matches = top_matches
        else: 
            for tm, score in top_matches.items():
                if tm not in aggregated_matches:
                    aggregated_matches[tm] = score
                else: 
                    current = aggregated_matches[tm]
                    aggregated_matches[tm] = current+score
    # Normalisation
    max_score = max(aggregated_matches.values())
    aggregated_matches = {tm: score/max_score for tm,score in aggregated_matches.items()}
    sorted_matches = sorted(aggregated_matches.items(), key=lambda item:item[1], reverse=True)
    return sorted_matches
    
# ========================= SHARED =========================     
def top_k_matches(top_matches=[]):  
    top_match = []
    similar_matches = []
    for i in range(len(top_matches)):
        if i == 0:
            top_match.append(top_matches[i][0])
            similar_matches.append(top_matches[i][0])
        else:
            if len(similar_matches) < 10:
                similar_matches.append(top_matches[i][0])
            else:
                break
    return top_match, [i.upper() for i in similar_matches if i.upper() != 'GENERAL HOLISTIC DEVELOPMENT']

def find_similar_cca(input=[]):
    top_prog, similar_ccas = top_k_matches(cca_similarity(input))
    return similar_ccas

def find_similar_prog(input=[]):
    top_prog, similar_progs = top_k_matches(prog_similarity(input))
    return similar_progs