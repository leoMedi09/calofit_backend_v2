from app.core.cache import get_user_recent_meals

meals = get_user_recent_meals(3)
print("=== REDIS CACHED MEALS ===")
for m in meals:
    print(m)
