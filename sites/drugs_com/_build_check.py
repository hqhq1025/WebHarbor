"""Rebuild and report counts."""
import os, sys

# Clean instance
import shutil
inst = "/work/instance"
if os.path.exists(inst):
    shutil.rmtree(inst)

import app
print("DRUGS_DATA:", len(app.DRUGS_DATA))
print("CONDITIONS_DATA:", len(app.CONDITIONS_DATA))
print("INTERACTIONS_DATA:", len(app.INTERACTIONS_DATA))

with app.app.app_context():
    print("drug:", app.Drug.query.count())
    print("interaction:", app.DrugInteraction.query.count())
    print("condition:", app.Condition.query.count())
    print("drug_class:", app.DrugClass.query.count())
    print("drug_image:", app.DrugImage.query.count())
    print("drug_review:", app.DrugReview.query.count())
    print("news_article:", app.NewsArticle.query.count())
    print("drug_condition:", app.DrugCondition.query.count())
    print("user:", app.User.query.count())
    print("saved_drug:", app.SavedDrug.query.count())
