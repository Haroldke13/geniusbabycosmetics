import os
from datetime import datetime
from urllib.parse import quote_plus

from flask import (
    Flask, render_template, request, redirect, url_for, flash, abort, jsonify
)
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
from bson.objectid import ObjectId
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config

from flask import Flask
from flask_pymongo import PyMongo
from config import Config
from mail_init import init_mail
from contact_bp import contact_bp
from payments_mpesa import mpesa_bp

mongo = PyMongo()

    


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Trust proxy headers on Render
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    # Mongo client & DB
    client = MongoClient(app.config["MONGO_URI"])
    db = client[app.config["MONGO_DB_NAME"]]
    app.mongo = db
    
    
    mongo.init_app(app)
    app.mongo = mongo.db

    init_mail(app)
    app.register_blueprint(contact_bp)
    app.register_blueprint(mpesa_bp)

    # Ensure indexes
    ensure_indexes(db)

    # Jinja helpers
    @app.template_filter("money")
    def money(value):
        try:
            return f"KSh {float(value):,.2f}"
        except Exception:
            return value

    @app.context_processor
    def inject_globals():
        return {
            "now_year": datetime.utcnow().year,
            "site_name": "GeniusBaby Cosmetics",
        }

    # Health check for Render
    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}, 200

    # Home - show featured and latest products
    @app.get("/")
    def home():
        featured = list(db.products.find({"is_featured": True}).sort("created_at", DESCENDING).limit(8))
        latest = list(db.products.find({}).sort("created_at", DESCENDING).limit(8))
        categories = db.products.distinct("category")
        brands = db.products.distinct("brand")
        return render_template("index.html", featured=featured, latest=latest, categories=categories, brands=brands)

    # Catalog with search, filters, pagination
    @app.get("/products")
    def products():
        q = request.args.get("q", "").strip()
        category = request.args.get("category", "").strip()
        brand = request.args.get("brand", "").strip()
        min_price = request.args.get("min_price", "").strip()
        max_price = request.args.get("max_price", "").strip()
        sort = request.args.get("sort", "newest").strip()
        page = max(1, int(request.args.get("page", 1)))
        per_page = max(1, min(60, int(request.args.get("per_page", app.config["PER_PAGE"]))))

        filters = {}
        if category:
            filters["category"] = category
        if brand:
            filters["brand"] = brand
        price_filter = {}
        if min_price:
            try:
                price_filter["$gte"] = float(min_price)
            except ValueError:
                pass
        if max_price:
            try:
                price_filter["$lte"] = float(max_price)
            except ValueError:
                pass
        if price_filter:
            filters["price"] = price_filter

        # Full-text or fallback regex search
        if q:
            # Prefer $text when possible
            filters["$text"] = {"$search": q}

        # Sorting
        sort_map = {
            "newest": ("created_at", DESCENDING),
            "price_asc": ("price", ASCENDING),
            "price_desc": ("price", DESCENDING),
            "rating": ("rating", DESCENDING),
            "name_asc": ("name", ASCENDING),
            "name_desc": ("name", DESCENDING),
        }
        sort_field, sort_dir = sort_map.get(sort, ("created_at", DESCENDING))

        total = db.products.count_documents(filters)
        cursor = (
            db.products.find(filters, {"score": {"$meta": "textScore"}} if q else None)
            .sort([(sort_field, sort_dir)])
            .skip((page - 1) * per_page)
            .limit(per_page)
        )
        items = list(cursor)

        pages = (total + per_page - 1) // per_page
        categories = db.products.distinct("category")
        brands = db.products.distinct("brand")
        return render_template(
            "products.html",
            items=items,
            total=total,
            page=page,
            pages=pages,
            per_page=per_page,
            q=q,
            category=category,
            brand=brand,
            min_price=min_price,
            max_price=max_price,
            sort=sort,
            categories=sorted([c for c in categories if c]),
            brands=sorted([b for b in brands if b]),
        )

    # Product detail by slug or id
    @app.get("/products/<slug_or_id>")
    def product_detail(slug_or_id):
        doc = None
        if ObjectId.is_valid(slug_or_id):
            doc = db.products.find_one({"_id": ObjectId(slug_or_id)})
        if not doc:
            doc = db.products.find_one({"slug": slug_or_id})
        if not doc:
            abort(404)
        related = list(db.products.find(
            {"category": doc.get("category"), "_id": {"$ne": doc["_id"]}}
        ).sort("created_at", DESCENDING).limit(8))
        return render_template("product_detail.html", item=doc, related=related)

    # Newsletter subscribe
    @app.post("/subscribe")
    def subscribe():
        email = request.form.get("email", "").strip().lower()
        if not email or "@" not in email:
            flash("Please provide a valid email address.", "warning")
            return redirect(request.referrer or url_for("home"))
        existing = db.subscribers.find_one({"email": email})
        if existing:
            flash("You're already subscribed. Thank you!", "info")
        else:
            db.subscribers.insert_one({"email": email, "created_at": datetime.utcnow()})
            flash("Subscribed successfully!", "success")
        return redirect(request.referrer or url_for("home"))

    # Contact form (store message)
    @app.post("/contact")
    def contact_submit():
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        message = request.form.get("message", "").strip()
        if not (name and email and message):
            flash("All fields are required.", "warning")
            return redirect(request.referrer or url_for("home"))
        db.contacts.insert_one({
            "name": name, "email": email, "message": message,
            "created_at": datetime.utcnow()
        })
        flash("Message sent! We'll get back to you soon.", "success")
        return redirect(request.referrer or url_for("home"))

    # Simple token-protected admin to create a product (form or JSON)
    @app.route("/admin/new", methods=["GET", "POST"])
    def admin_new():
        token = request.headers.get("X-Admin-Token") or request.args.get("token")
        if token != app.config["ADMIN_TOKEN"]:
            abort(403)
        if request.method == "GET":
            return render_template("admin_new_product.html")
        # POST
        form = request.form
        name = form.get("name", "").strip()
        if not name:
            flash("Name is required", "warning")
            return redirect(url_for("admin_new"))
        doc = {
            "name": name,
            "slug": slugify(form.get("slug") or name),
            "brand": form.get("brand", "").strip(),
            "category": form.get("category", "").strip(),
            "price": float(form.get("price", "0") or 0),
            "sale_price": float(form.get("sale_price", "0") or 0),
            "description": form.get("description", "").strip(),
            "ingredients": form.get("ingredients", "").strip(),
            "skin_type": form.get("skin_type", "").strip(),
            "image_url": form.get("image_url", "").strip() or url_for("static", filename="img/placeholder.svg"),
            "rating": float(form.get("rating", "4.8") or 4.8),
            "stock": int(form.get("stock", "100") or 100),
            "is_featured": bool(form.get("is_featured")),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        existing = app.mongo.products.find_one({"slug": doc["slug"]})
        if existing:
            flash("A product with that slug already exists.", "danger")
            return redirect(url_for("admin_new"))
        app.mongo.products.insert_one(doc)
        flash("Product created.", "success")
        return redirect(url_for("product_detail", slug_or_id=doc["slug"]))

    return app


def ensure_indexes(db):
    # Create helpful indexes if not present
    try:
        db.products.create_index([("slug", ASCENDING)], name="slug_unique", unique=True)
        db.products.create_index([("brand", ASCENDING)], name="brand_idx")
        db.products.create_index([("category", ASCENDING)], name="category_idx")
        db.products.create_index([("created_at", DESCENDING)], name="created_at_idx")
        db.products.create_index([("name", TEXT), ("brand", TEXT), ("description", TEXT)], name="text_search")
        db.subscribers.create_index([("email", ASCENDING)], name="email_unique", unique=True)
        db.contacts.create_index([("created_at", DESCENDING)], name="contact_created_at_idx")
    except Exception as e:
        # Index errors shouldn't crash app on boot
        print("Index creation error:", e)


def slugify(s: str) -> str:
    import re, unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s


   