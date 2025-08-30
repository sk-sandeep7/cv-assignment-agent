import json
import random
import difflib

# Load bank
with open("./examples.json") as f:
    data = json.load(f)
qbank = json.loads(data) if isinstance(data, str) else data


def score_question(q, user_topics):
    # Handle case where topic might be missing, None, or a single string
    raw_topics = q['topic']
    if isinstance(raw_topics, str):
        q_topics = {raw_topics.lower()}
    elif isinstance(raw_topics, list):
        q_topics = {str(t).lower() for t in raw_topics}
    else:
        q_topics = set()

    u_topics = {str(t).lower() for t in user_topics}
    return len(q_topics & u_topics)

def match_topics_fuzzy(user_topics, known_topics, cutoff=0.6):
    matched = set()
    for topic in user_topics:
        closest = difflib.get_close_matches(topic, known_topics, n=1, cutoff=cutoff)
        if closest:
            matched.add(closest[0])
    return list(matched)

def select_few_shots(user_topics, k=3, as_json=False, seed=None):
    if seed is not None:
        random.seed(seed)  # reproducibility if needed

    all_known_topics = {t.lower() for q in qbank for t in (q['topic'] if isinstance(q['topic'], list) else [q['topic']])}
    
    matched_topics = match_topics_fuzzy([t.lower() for t in user_topics], all_known_topics)

    if matched_topics:
        filtered = [q for q in qbank if any(t.lower() in [topic.lower() for topic in (q['topic'] if isinstance(q['topic'], list) else [q['topic']])] for t in matched_topics)]
    else:
        # Fallback to a few default topics if no match is found
        fallback_topics = ["computer vision", "convolutional neural networks"]
        filtered = [q for q in qbank if any(t.lower() in [topic.lower() for topic in (q['topic'] if isinstance(q['topic'], list) else [q['topic']])] for t in fallback_topics)]

    # If still no questions, return a random sample from the entire bank
    if not filtered:
        filtered = qbank

    few_shots = random.sample(filtered, min(k, len(filtered)))

    return json.dumps(few_shots, indent=2) if as_json else few_shots


# Example usage
user_topics = ["Digital Image Processing", "Convolution", "FAST"]

few_shots_dicts = select_few_shots(user_topics, k=3, as_json=True, seed=None)
print("Random relevant few-shots (JSON):")
print(few_shots_dicts)
