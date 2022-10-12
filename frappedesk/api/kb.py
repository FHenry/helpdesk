import frappe
from frappe.model.rename_doc import rename_doc
import json


@frappe.whitelist()
def update_category(old_category_name, new_category_name, new_description):
	category_doc = frappe.get_doc("Category", old_category_name)
	category_doc.category_name = new_category_name
	category_doc.description = new_description
	category_doc.save()

	if old_category_name != new_category_name:
		rename_doc("Category", old_category_name, new_category_name)


@frappe.whitelist()
def delete_category(category):
	artiles = frappe.get_all(
		"Article", filters={"category": ["=", category]}, pluck="name"
	)
	if len(artiles) != 0:
		raise Exception("Cannot delete category with articles")
	else:
		frappe.delete_doc("Category", category)


@frappe.whitelist()
def check_if_article_title_exists(name, title):
	filters = {"title": ["=", title]}
	if name:
		filters["name"] = ["!=", name]

	return frappe.db.exists("Article", filters)


@frappe.whitelist()
def insert_new_update_existing_categories(new_values, old_values):
	# TODO: optimize this

	# set idx values for all the new_values based on index
	for i in range(len(new_values)):
		new_values[i]["idx"] = i

	to_insert = [
		{key: val for key, val in c.items() if key != "is_new"}
		for c in new_values
		if "is_new" in c
	]
	to_update = [c for c in new_values if "is_new" not in c]

	names_in_old_values = [c["name"] for c in old_values]
	names_in_new_values = [c["name"] if "name" in c else "" for c in new_values]

	to_archive = [c for c in names_in_old_values if c not in names_in_new_values]

	# validate and delete missing categories
	for category in to_archive:
		if frappe.db.exists("Category", {"name": category, "parent_category": category}):
			raise Exception("Cannot archive category with subcategories")
		elif frappe.db.exists("Article", {"category": category}):
			raise Exception("Cannot archive category with articles")
		else:
			frappe.get_doc("Category", category).archive()

	# create new categories if present
	for category in to_insert:
		doc = frappe.new_doc("Category")
		doc.update(category)
		doc.save()

	# update description & category_name
	for category in to_update:
		doc = frappe.get_doc("Category", category["name"])
		doc.update(category)
		doc.save()

	return


@frappe.whitelist()
def update_articles_order_and_status(new_values):
	# set idx values after filtering out articles marked as draft
	to_update = [c for c in new_values if c["status"] == "Published"]
	for i in range(len(to_update)):
		to_update[i]["idx"] = i

	for article in to_update:
		doc = frappe.get_doc("Article", article["name"])
		doc.update(article)
		doc.save()

	to_mark_as_draft = [c["name"] for c in new_values if c["status"] == "Draft"]

	for article in to_mark_as_draft:
		doc = frappe.get_doc("Article", article)
		doc.status = "Draft"
		doc.idx = -1
		doc.save()

	return


@frappe.whitelist(allow_guest=True)
def get_breadcrumbs(docType, docName):
	if docType not in ["Article", "Category"]:
		frappe.throw("Doctype should be either Article or Category")
	return frappe.get_doc(docType, docName).get_breadcrumbs()
