import pickle
with open("model.pkl","rb") as model_pk:
    model = pickle.load(model_pk)
type(model)
def predict(sent):
    return model.kneighbors(sent)