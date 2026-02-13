import sys
import os
from sqlalchemy.orm import Session

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app import models

def populate_azure_subscriptions():
    subscriptions = {
        "d6726f33-ec06-4fb2-af7e-664e02345f9f": "Saviynt Azure(Converted to EA)",
        "5f631bbd-2718-4f23-a45c-2c3a15f72b32": "Saviynt Cloud Engineering RnD",
        "9b774a4b-7b07-49eb-9482-519848f4a358": "Saviynt-Airgap-RnD",
        "6645e7e4-5493-4787-bb1a-537a7db196cf": "Saviynt-Atlantis",
        "9c6d9717-e206-4fc1-a171-d9bfc911c4af": "Saviynt-Computacenter",
        "d5af95f9-292c-4784-bbc6-49cdf5ffd5b9": "Saviynt-Customer-Infra1",
        "6f96909e-f629-4863-9433-09f32b18fcff": "Saviynt-Customer-Infra2",
        "a61100e9-372e-4097-bfae-5d1db86a6c29": "Saviynt-Customer-Infra3",
        "d489a9f6-4807-403c-89ab-a2fd9f80b825": "Saviynt-Customer-Infra4",
        "de7f2e1a-6644-4b21-84d8-904b4bde217b": "Saviynt-Customer-Infra5",
        "cd5344ad-6663-44c1-bace-e02ad8418609": "Saviynt-Customer-Infra6",
        "3bab3b11-dbd8-49f6-8e5c-450c3cff6929": "Saviynt-Customer-Infra7",
        "8c726af8-97f0-4676-8a6e-5ac889027b89": "Saviynt-Engineering",
        "7d8cfb31-95c8-4428-b8ef-30ec5a5ab3d5": "Saviynt-HCA",
        "f9aae678-fb6e-4361-bfd1-5761461b5102": "Saviynt-ISPM-CC",
        "1815fa90-d3cc-4cd3-867d-f940d0f1b807": "Saviynt-Olympus",
        "a5447eff-ac6b-471c-b220-6e70c8fd6a7c": "Saviynt-Pentest",
        "f03ee452-9270-49bb-8dae-a969429589b0": "Saviynt-POC"
    }
    
    internal_names = {
        "Saviynt Cloud Engineering RnD",
        "Saviynt-Airgap-RnD", 
        "Saviynt-Engineering",
        "Saviynt-POC",
        "Saviynt-SRE",
        "Saviynt-Pentest"
    }
    
    db: Session = SessionLocal()
    
    try:
        for sub_id, sub_name in subscriptions.items():
            existing = db.query(models.AzureSubscription).filter(models.AzureSubscription.id == sub_id).first()
            if not existing:
                subscription = models.AzureSubscription(
                    id=sub_id,
                    subscription_name=sub_name,
                    is_internal=sub_name in internal_names
                )
                db.add(subscription)
        
        db.commit()
        print("Azure subscriptions populated successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    populate_azure_subscriptions()