import xmlrpc.client
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from mcp.server.fastmcp import FastMCP, Context
# Tambahkan setelah import yang sudah ada (setelah baris "from mcp.server.fastmcp import FastMCP, Context")
import base64
from io import BytesIO
try:
    import pypdf
    PdfReader = pypdf.PdfReader
except ImportError:
    PdfReader = None

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

@dataclass
class OdooConnection:
    url: str
    db: str
    username: str
    password: str
    uid: int = 0
    models: xmlrpc.client.ServerProxy = None
    common: xmlrpc.client.ServerProxy = None

    def connect(self):
        """Establish connection to Odoo"""
        self.common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
        self.uid = self.common.authenticate(self.db, self.username, self.password, {})
        if not self.uid:
            raise Exception("Failed to authenticate with Odoo")
        self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
        return self

    def execute(self, model, method, *args, **kwargs):
        """Execute method on model"""
        return self.models.execute_kw(
            self.db, self.uid, self.password, 
            model, method, args, kwargs
        )

@asynccontextmanager
async def odoo_lifespan(server: FastMCP) -> AsyncIterator[OdooConnection]:
    """Manage Odoo connection lifecycle"""
    # Get connection details from environment or config
    import os
    
    # Log environment variables for debugging
    env_vars = {k: v for k, v in os.environ.items() if k.startswith('ODOO_')}
    print(f"Available Odoo environment variables: {env_vars.keys()}")
    
    # Check for both ODOO_USER and ODOO_USERNAME for compatibility
    odoo_url = os.environ.get('ODOO_URL', 'http://localhost:8069')
    odoo_db = os.environ.get('ODOO_DB', 'odoo')
    
    # Try both variable names - either ODOO_USER or ODOO_USERNAME
    odoo_user = os.environ.get('ODOO_USER')
    if odoo_user is None:
        odoo_user = os.environ.get('ODOO_USERNAME', 'admin')
        if odoo_user != 'admin':  # If we found ODOO_USERNAME
            print("Using ODOO_USERNAME instead of ODOO_USER")
    
    odoo_password = os.environ.get('ODOO_PASSWORD', 'admin')
    
    print(f"Connecting to Odoo at {odoo_url} with DB: {odoo_db}, User: {odoo_user}")
    
    # Create and initialize connection
    odoo = OdooConnection(odoo_url, odoo_db, odoo_user, odoo_password)
    try:
        print("Attempting to connect to Odoo...")
        odoo.connect()
        print(f"Successfully connected to Odoo as UID: {odoo.uid}")
        yield odoo
    except Exception as e:
        print(f"Error connecting to Odoo: {str(e)}")
        # Create minimal odoo connection for basic functionality
        # This way some functions might still work even with connection issues
        yield OdooConnection(odoo_url, odoo_db, odoo_user, odoo_password)
    finally:
        # No explicit cleanup needed for XML-RPC
        print("Odoo connection cleanup")
        pass

# Create MCP server with Odoo context
mcp = FastMCP("Odoo Explorer", lifespan=odoo_lifespan)

# --------- RESOURCES ---------

@mcp.resource("odoo://models")
def list_models() -> str:
    """List all available models in Odoo"""
    odoo = mcp.app.lifespan_context
    models = odoo.execute('ir.model', 'search_read', [], ['name', 'model', 'description'])
    
    result = "# Available Odoo Models\n\n"
    for model in models:
        result += f"## {model['name']} (`{model['model']}`)\n"
        if model.get('description'):
            result += f"{model['description']}\n"
        result += "\n"
    
    return result

@mcp.resource("odoo://model/{model}/schema")
def get_model_schema(model: str) -> str:
    """
    Get schema for a specific Odoo model
    
    Args:
        model: The technical name of the Odoo model (e.g., 'res.partner', 'product.product')
    
    Examples:
        odoo://model/res.partner/schema
        odoo://model/sale.order/schema
    """
    odoo = mcp.app.lifespan_context
    
    # Get model info
    model_info = odoo.execute('ir.model', 'search_read', 
                              [('model', '=', model)], 
                              ['name', 'description'])
    
    if not model_info:
        return f"Error: Model '{model}' not found"
    
    # Get fields info
    fields = odoo.execute(model, 'fields_get', [], 
                         ['string', 'help', 'type', 'required', 'relation'])
    
    # Format as markdown
    result = f"# {model_info[0]['name']} (`{model}`)\n\n"
    if model_info[0].get('description'):
        result += f"{model_info[0]['description']}\n\n"
    
    result += "## Fields\n\n"
    result += "| Field | Type | Required | Description |\n"
    result += "| ----- | ---- | -------- | ----------- |\n"
    
    for field_name, field_info in fields.items():
        field_type = field_info['type']
        if field_type in ['many2one', 'one2many', 'many2many'] and field_info.get('relation'):
            field_type = f"{field_type} ({field_info['relation']})"
        
        required = "Yes" if field_info.get('required') else "No"
        description = field_info.get('help', '')
        
        result += f"| {field_name} | {field_type} | {required} | {description} |\n"
    
    return result

@mcp.resource("odoo://model/{model}/records/count")
def get_record_count(model: str) -> str:
    """Get the number of records in a model"""
    odoo = mcp.app.lifespan_context
    count = odoo.execute(model, 'search_count', [])
    return f"# Record Count for {model}\n\nTotal records: {count}"

# --------- TOOLS ---------

@mcp.tool()
def search_records(ctx: Context, model: str, domain: List = None, limit: int = 1000, fields: List[str] = None) -> str:
    """
    Search for records in an Odoo model
    
    Args:
        model: Odoo model name (e.g., 'res.partner', 'product.product', 'sale.order')
        domain: Domain filter as a list of triplets (e.g., [['is_company', '=', True], ['customer_rank', '>', 0]])
               Format: [[field_name, operator, value], ...] 
               Common operators: =, !=, >, >=, <, <=, like, ilike, in, not in
        limit: Maximum number of records to return (default: 1000)
        fields: List of fields to fetch (e.g., ['id', 'name', 'email']). If empty, returns all non-binary fields
    
    Examples:
        search_records(model="res.partner", domain=[["is_company", "=", true], ["country_id.code", "=", "US"]], limit=10)
        search_records(model="product.product", fields=["name", "list_price", "default_code"])
        search_records(model="sale.order", domain=[["state", "=", "sale"]], fields=["name", "partner_id", "amount_total"])
    """
    
    try:
        # Log mulai pencarian dengan parameter
        ctx.info(f"Searching {model} with domain: {domain}, limit: {limit}, fields: {fields}")
        
        odoo = ctx.request_context.lifespan_context
        
        # Default domain and fields if not provided
        if domain is None:
            domain = []
        if fields is None:
            # Get model fields first
            try:
                available_fields = odoo.execute(model, 'fields_get', [], ['type'])
                # Filter out binary fields that could be large
                fields = [f for f, info in available_fields.items() 
                         if info.get('type') not in ['binary']]
            except Exception as field_error:
                ctx.error(f"Error getting fields for {model}: {str(field_error)}")
                fields = ['id', 'name', 'display_name']  # Fallback to basic fields
        
        # Execute search with timeout handling
        try:
            ctx.info(f"Executing search_read on {model}")
            records = odoo.execute(model, 'search_read', domain, fields, 0, limit)
            ctx.info(f"Got {len(records)} records")
        except Exception as search_error:
            ctx.error(f"Search error: {str(search_error)}")
            return f"Error searching records in {model}: {str(search_error)}"
        
        if not records:
            return f"No records found for {model} with the given domain."
        
        # Format results as a table
        result = f"# Search Results for {model}\n\n"
        result += f"Found {len(records)} records (limit: {limit}).\n\n"
        
        # Get column headers (fields)
        headers = list(records[0].keys())
        
        # Format as markdown table
        result += "| " + " | ".join(headers) + " |\n"
        result += "| " + " | ".join(["---" for _ in headers]) + " |\n"
        
        # Add rows
        for record in records:
            row = []
            for field in headers:
                value = record.get(field, "")
                # Format the value to be table-friendly
                if isinstance(value, (list, tuple)):
                    if len(value) == 2 and isinstance(value[0], int) and isinstance(value[1], str):
                        # This is likely a Many2one field (id, name)
                        value = value[1]
                    else:
                        value = str(value)
                elif value is False:
                    value = ""
                row.append(str(value).replace("|", "\\|"))
            
            result += "| " + " | ".join(row) + " |\n"
        
        return result
    except Exception as e:
        error_message = f"Error in search_records: {str(e)}"
        ctx.error(error_message)
        return error_message

@mcp.tool()
def run_report(ctx: Context, model: str, report_name: str, domain: List = None, group_by: List[str] = None, 
             measures: List[str] = None) -> str:
    """
    Run a simple aggregation report on Odoo model data
    
    Args:
        model: Odoo model name (e.g., 'sale.order', 'purchase.order', 'account.move')
        report_name: A descriptive name for this report that will appear as the title
        domain: Domain filter as a list of triplets (e.g., [['state', '=', 'sale'], ['date_order', '>=', '2023-01-01']])
               Format: [[field_name, operator, value], ...]
        group_by: Fields to group by (e.g., ['partner_id', 'user_id']) - REQUIRED
        measures: Numeric fields to aggregate (e.g., ['amount_total', 'amount_untaxed'])
    
    Examples:
        run_report(
            model="sale.order", 
            report_name="Sales by Customer", 
            domain=[["state", "=", "sale"]], 
            group_by=["partner_id"], 
            measures=["amount_total"]
        )
        
        run_report(
            model="account.move", 
            report_name="Invoices by Month", 
            domain=[["type", "=", "out_invoice"], ["state", "=", "posted"]], 
            group_by=["invoice_date_month"], 
            measures=["amount_total"]
        )
    """
    try:
        ctx.info(f"Running report on {model} with domain: {domain}, group_by: {group_by}, measures: {measures}")
        
        odoo = ctx.request_context.lifespan_context
        
        if domain is None:
            domain = []
        
        if not group_by:
            return "Error: group_by is required for reports"
        
        result = f"# {report_name}\n\n"
        
        # Get records
        all_fields = group_by.copy()
        if measures:
            all_fields.extend(measures)
        
        try:
            ctx.info(f"Fetching data from {model} with fields: {all_fields}")
            records = odoo.execute(model, 'search_read', domain, all_fields)
            ctx.info(f"Got {len(records)} records for report")
        except Exception as search_error:
            ctx.error(f"Error fetching records: {str(search_error)}")
            return f"Error fetching data for report: {str(search_error)}"
        
        if not records:
            return f"No data found for model {model} with the given criteria."
        
        # Simple aggregation implementation in Python
        try:
            ctx.info("Performing aggregation")
            groups = {}
            for record in records:
                # Create group key
                group_key = tuple(str(record.get(field, '')) for field in group_by)
                
                if group_key not in groups:
                    groups[group_key] = {
                        'count': 0,
                        'values': {m: [] for m in measures} if measures else {}
                    }
                    # Add group_by values
                    for field in group_by:
                        groups[group_key][field] = record.get(field)
                
                # Increment count
                groups[group_key]['count'] += 1
                
                # Collect measure values
                if measures:
                    for measure in measures:
                        value = record.get(measure)
                        if isinstance(value, (int, float)):
                            groups[group_key]['values'][measure].append(value)
        except Exception as agg_error:
            ctx.error(f"Error in aggregation: {str(agg_error)}")
            return f"Error performing aggregation for report: {str(agg_error)}"
        
        # Generate the report
        try:
            ctx.info("Generating report output")
            result += "| " + " | ".join(group_by) + " | Count |"
            if measures:
                for measure in measures:
                    result += f" Sum ({measure}) | Avg ({measure}) |"
            result += "\n"
            
            result += "| " + " | ".join(["---" for _ in group_by]) + " | --- |"
            if measures:
                for _ in measures:
                    result += " --- | --- |"
            result += "\n"
            
            for group_key, group_data in groups.items():
                row = []
                for field in group_by:
                    value = group_data.get(field, "")
                    if isinstance(value, (list, tuple)) and len(value) == 2:
                        value = value[1]  # Many2one case
                    elif value is False:
                        value = ""
                    row.append(str(value).replace("|", "\\|"))
                
                row.append(str(group_data['count']))
                
                if measures:
                    for measure in measures:
                        values = group_data['values'].get(measure, [])
                        if values:
                            row.append(str(sum(values)))
                            row.append(str(round(sum(values) / len(values), 2)))
                        else:
                            row.append("")
                            row.append("")
                
                result += "| " + " | ".join(row) + " |\n"
        except Exception as output_error:
            ctx.error(f"Error generating report output: {str(output_error)}")
            return f"Error generating report output: {str(output_error)}"
        
        return result
    except Exception as e:
        error_message = f"Error in run_report: {str(e)}"
        ctx.error(error_message)
        return error_message
    
@mcp.tool()
def get_contextual_metadata(ctx: Context, keywords: List[str], depth: int = 2) -> str:
    """
    Mengambil metadata dan ERD kontekstual untuk model-model yang terkait dengan kata kunci yang diberikan
    
    Args:
        keywords: Daftar kata kunci untuk mencari model yang relevan (misal: ['sale', 'invoice'])
        depth: Kedalaman relasi yang akan diambil (default: 2)
    
    Examples:
        get_contextual_metadata(keywords=["sale", "order"])
        get_contextual_metadata(keywords=["partner", "customer"], depth=1)
        get_contextual_metadata(keywords=["invoice", "payment"], depth=3)
    
    Returns:
        Metadata model dan relasi dalam format Markdown
    """
    try:
        ctx.info(f"Getting contextual metadata for keywords: {keywords}, depth: {depth}")
        odoo = ctx.request_context.lifespan_context
        
        # Langkah 1: Temukan model yang cocok dengan kata kunci
        matching_models = []
        all_models = odoo.execute('ir.model', 'search_read', [], ['name', 'model', 'info'])
        
        for model_data in all_models:
            model_name = model_data.get('model', '')
            display_name = model_data.get('name', '')
            
            # Periksa apakah model cocok dengan salah satu kata kunci
            if any(keyword.lower() in model_name.lower() or 
                   keyword.lower() in display_name.lower() 
                   for keyword in keywords):
                matching_models.append(model_data)
        
        if not matching_models:
            return f"No models found matching the keywords: {keywords}"
        
        # Langkah 2: Kumpulkan metadata untuk model yang cocok dan relasinya
        metadata = {}
        related_models = set()
        
        for model_data in matching_models:
            model_name = model_data.get('model')
            related_models.add(model_name)
        
        # Kumpulkan model terkait sampai kedalaman yang ditentukan
        current_depth = 0
        while current_depth < depth:
            new_related = set()
            
            for model_name in related_models:
                if model_name not in metadata:
                    try:
                        # Dapatkan info field untuk model ini
                        fields_info = odoo.execute(model_name, 'fields_get', [], 
                                                ['string', 'help', 'type', 'required', 'relation'])
                        
                        metadata[model_name] = {
                            'name': model_name,
                            'fields': fields_info
                        }
                        
                        # Tambahkan model terkait untuk iterasi berikutnya
                        for field_name, field_info in fields_info.items():
                            if field_info.get('type') in ['many2one', 'one2many', 'many2many'] and field_info.get('relation'):
                                new_related.add(field_info['relation'])
                    except Exception as e:
                        ctx.error(f"Error fetching fields for {model_name}: {str(e)}")
            
            # Tambahkan model terkait baru
            related_models.update(new_related)
            current_depth += 1
        
        # Langkah 3: Format hasil sebagai markdown
        result = f"# Contextual Entity Relationship Diagram (ERD) for keywords: {', '.join(keywords)}\n\n"
        result += f"Total related models found: {len(metadata)}\n\n"
        
        # Tampilkan model dan field-nya
        for model_name, model_info in metadata.items():
            result += f"## {model_name}\n\n"
            
            # Tampilkan fields
            result += "### Fields\n\n"
            result += "| Field Name | Type | Required | Description |\n"
            result += "|------------|------|----------|-------------|\n"
            
            for field_name, field_info in model_info['fields'].items():
                field_type = field_info.get('type', '')
                
                # Tambahkan info relasi jika ada
                if field_type in ['many2one', 'one2many', 'many2many'] and field_info.get('relation'):
                    field_type = f"{field_type} → {field_info['relation']}"
                
                required = "Yes" if field_info.get('required') else "No"
                description = field_info.get('help', '') or field_info.get('string', '')
                
                result += f"| {field_name} | {field_type} | {required} | {description} |\n"
            
            result += "\n"
        
        # Langkah 4: Tambahkan ringkasan relasi
        result += "## Model Relationships\n\n"
        for model_name, model_info in metadata.items():
            relations = []
            
            for field_name, field_info in model_info['fields'].items():
                if field_info.get('type') in ['many2one', 'one2many', 'many2many'] and field_info.get('relation'):
                    relation_type = field_info['type']
                    related_model = field_info['relation']
                    
                    if related_model in metadata:  # Hanya tampilkan relasi ke model yang juga dalam metadata
                        relations.append(f"- **{relation_type}** via `{field_name}` to **{related_model}**")
            
            if relations:
                result += f"### {model_name}\n"
                result += "\n".join(relations) + "\n\n"
        
        return result
    except Exception as e:
        error_message = f"Error in get_contextual_metadata: {str(e)}"
        ctx.error(error_message)
        return error_message

@mcp.tool()
def advanced_query(ctx: Context, main_model: str, fields: List[str], joins: List[Dict] = None, 
                 filters: List = None, group_by: List[str] = None, aggregations: Dict = None,
                 limit: int = None, order: str = None) -> str:
    """
    Melakukan query lanjutan dengan dukungan untuk join antar model, filter kompleks, dan agregasi
    
    Args:
        main_model: Model utama untuk query (misal: 'sale.order')
        fields: Daftar field untuk diambil, termasuk field relasi dengan notasi dot (misal: 'partner_id.name')
        joins: Daftar model yang akan di-join dengan format [{"model": "nama_model", "link_field": "field_relasi"}, ...]
        filters: Domain filter dengan format Odoo [[field, operator, value], ...] 
        group_by: Field untuk group by (misal: ['partner_id', 'date_month'])
        aggregations: Operasi agregasi untuk field numerik {"field": ["sum", "avg"], ...}
        limit: Batas jumlah record yang diambil (default: 100)
        order: Field dan arah pengurutan (misal: 'date_order desc, id')
    
    Examples:
        advanced_query(
            main_model="sale.order",
            fields=["name", "partner_id.name", "amount_total"],
            filters=[["date_order", ">=", "2025-01-01"]],
            order="date_order desc",
            limit=10
        )
        
        advanced_query(
            main_model="sale.order",
            fields=["partner_id.name", "amount_total"],
            group_by=["partner_id"],
            aggregations={"amount_total": ["sum", "avg"]},
            filters=[["date_order", ">=", "2025-01-01"]]
        )
    """
    try:
        ctx.info(f"Running advanced query on {main_model}")
        odoo = ctx.request_context.lifespan_context
        
        # Default values
        if joins is None:
            joins = []
        if filters is None:
            filters = []
        
        # Langkah 1: Persiapkan query dengan field relasi
        query_fields = []
        field_mapping = {}  # Untuk menangani field dari relasi
        
        for field in fields:
            if '.' in field:
                # Ini adalah field relasi (misal partner_id.name)
                parts = field.split('.')
                relation_field = parts[0]  # field relasi (partner_id)
                sub_field = parts[1]  # field dari model yang berelasi (name)
                
                # Pastikan relasi field ada dalam query fields
                if relation_field not in query_fields:
                    query_fields.append(relation_field)
                
                # Catat mapping untuk hasil akhir
                if relation_field not in field_mapping:
                    field_mapping[relation_field] = []
                field_mapping[relation_field].append(sub_field)
            else:
                # Field normal
                query_fields.append(field)
        
        # Langkah 2: Buat domain untuk filter
        domain = filters
        
        # Langkah 3: Jalankan query sesuai kondisi
        if group_by and aggregations:
            # Query dengan agregasi
            result = "# Query Result with Aggregation\n\n"
            
            # Ini adalah implementasi sederhana, untuk implementasi sebenarnya
            # mungkin perlu menggunakan read_group Odoo API
            records = odoo.execute(main_model, 'search_read', domain, query_fields, 0, limit, order)
            
            # Proses agregasi secara manual (sebagai contoh sederhana)
            groups = {}
            for record in records:
                # Buat key untuk grup
                group_key = []
                for gb_field in group_by:
                    value = record.get(gb_field)
                    if isinstance(value, tuple) and len(value) == 2:  # Many2one field
                        value = value[1]  # Ambil display name
                    group_key.append(str(value))
                
                group_key = tuple(group_key)
                if group_key not in groups:
                    groups[group_key] = {
                        'count': 0,
                        'values': {field: [] for field in aggregations.keys()}
                    }
                    # Tambahkan field group by
                    for i, gb_field in enumerate(group_by):
                        groups[group_key][gb_field] = record.get(gb_field)
                
                # Tambah count
                groups[group_key]['count'] += 1
                
                # Kumpulkan nilai untuk agregasi
                for agg_field in aggregations.keys():
                    value = record.get(agg_field)
                    if isinstance(value, (int, float)):
                        groups[group_key]['values'][agg_field].append(value)
            
            # Buat tabel hasil
            headers = []
            for gb_field in group_by:
                headers.append(gb_field)
            
            headers.append("Count")
            
            for agg_field, operations in aggregations.items():
                for op in operations:
                    headers.append(f"{op}({agg_field})")
            
            result += "| " + " | ".join(headers) + " |\n"
            result += "| " + " | ".join(["---" for _ in headers]) + " |\n"
            
            # Tambahkan data
            for group_key, group_data in groups.items():
                row = []
                for i, gb_field in enumerate(group_by):
                    value = group_data.get(gb_field, "")
                    if isinstance(value, tuple) and len(value) == 2:
                        value = value[1]  # Many2one case
                    row.append(str(value).replace("|", "\\|"))
                
                row.append(str(group_data['count']))
                
                for agg_field, operations in aggregations.items():
                    values = group_data['values'].get(agg_field, [])
                    for op in operations:
                        if op == "sum" and values:
                            row.append(str(sum(values)))
                        elif op == "avg" and values:
                            row.append(str(round(sum(values) / len(values), 2)))
                        else:
                            row.append("")
                
                result += "| " + " | ".join(row) + " |\n"
        else:
            # Query biasa tanpa agregasi
            records = odoo.execute(main_model, 'search_read', domain, query_fields, 0, limit, order)
            
            # Resolve related fields
            for record in records:
                for relation_field, sub_fields in field_mapping.items():
                    relation_value = record.get(relation_field)
                    
                    # Jika relasi adalah many2one, maka nilainya adalah tuple (id, name)
                    if isinstance(relation_value, tuple) and len(relation_value) == 2:
                        for sub_field in sub_fields:
                            if sub_field == 'name':
                                record[f"{relation_field}.{sub_field}"] = relation_value[1]
                            else:
                                # Untuk sub_field selain 'name', kita perlu query tambahan
                                # Ini hanya contoh sederhana, implementasi sebenarnya perlu lebih kompleks
                                record[f"{relation_field}.{sub_field}"] = f"[{sub_field} of {relation_value[1]}]"
            
            # Format hasil sebagai tabel markdown
            result = f"# Query Results for {main_model}\n\n"
            result += f"Found {len(records)} records (limit: {limit}).\n\n"
            
            if not records:
                return "No records found matching the criteria."
            
            # Get column headers, termasuk field relasi yang diresolved
            headers = []
            for field in fields:
                headers.append(field)
            
            # Format as markdown table
            result += "| " + " | ".join(headers) + " |\n"
            result += "| " + " | ".join(["---" for _ in headers]) + " |\n"
            
            # Add rows
            for record in records:
                row = []
                for field in fields:
                    # Ambil nilai field, baik biasa maupun relasi yang sudah diresolved
                    value = record.get(field, "")
                    
                    # Format value untuk tabel
                    if isinstance(value, tuple) and len(value) == 2:
                        # Many2one field
                        value = value[1]
                    elif isinstance(value, list):
                        value = str(value)
                    elif value is False:
                        value = ""
                    
                    row.append(str(value).replace("|", "\\|"))
                
                result += "| " + " | ".join(row) + " |\n"
        
        return result
    except Exception as e:
        error_message = f"Error in advanced_query: {str(e)}"
        ctx.error(error_message)
        return error_message

@mcp.tool()
def read_document(ctx: Context, document_id: int = None, document_name: str = None, 
                folder_id: int = None, limit_chars: int = None) -> str:
    """
    Membaca isi dokumen PDF/DOCX dari modul 'documents.document' Odoo.
    Jangan batasi jumlah teks yang diekstrak!
    
    Args:
        document_id: ID dokumen yang akan dibaca (opsional jika document_name diisi)
        document_name: Nama dokumen untuk dicari (opsional jika document_id diisi)
        folder_id: ID folder untuk membatasi pencarian (opsional)
    
    Examples:
        read_document(document_id=123)
        read_document(document_name="SOP Rekrutmen", folder_id=5)
        read_document(document_name="Pedoman", folder_id=5)
    
    Returns:
        Isi teks dari dokumen dalam format markdown
    """
    try:
        # Force unlimited character reading regardless of any limit_chars parameter
        ctx.info("Forcing unlimited character reading for document")
        
        # Ambil parameter tambahan dari request jika ada
        request_params = getattr(ctx.request_context, 'params', {}) or {}
        
        # Jika limit_chars ada, ganti dengan nilai sangat besar
        if 'limit_chars' in request_params:
            ctx.info(f"Overriding limit_chars from {request_params['limit_chars']} to unlimited")
            request_params['limit_chars'] = None  # 10 juta karakter, praktis unlimited
        
        request_params['limit_chars'] = None
        ctx.info(f"Reading document content. ID: {document_id}, Name: {document_name}, Folder: {folder_id}")
        odoo = ctx.request_context.lifespan_context
        
        # Langkah 1: Temukan dokumen berdasarkan parameter
        domain = []
        if document_id:
            domain.append(['id', '=', document_id])
        if document_name:
            domain.append(['name', 'ilike', document_name])
        if folder_id:
            domain.append(['folder_id', '=', folder_id])
        
        if not domain:
            return "Error: Harus menentukan document_id atau document_name"
        
        # Jika ada lebih dari satu kondisi, gabungkan dengan AND
        if len(domain) > 1:
            domain = ['&'] * (len(domain) - 1) + domain
        
        document = odoo.execute('documents.document', 'search_read', domain, 
                               ['name', 'mimetype', 'datas', 'attachment_id'], 0, 1)
        
        if not document:
            return f"Dokumen tidak ditemukan dengan kriteria: ID={document_id}, Name={document_name}, Folder={folder_id}"
        
        document = document[0]
        
        # Langkah 2: Dapatkan binary content dari attachment
        attachment_id = document.get('attachment_id')
        if not attachment_id or not isinstance(attachment_id, (list, tuple)) or len(attachment_id) != 2:
            return f"Dokumen ditemukan tetapi tidak memiliki attachment: {document['name']}"
        
        attachment_data = odoo.execute('ir.attachment', 'read', [attachment_id[0]], ['datas'])
        
        if not attachment_data or not attachment_data[0].get('datas'):
            return f"Attachment ditemukan tetapi tidak ada data binary: {document['name']}"
        
        # Langkah 3: Dekode binary data
        try:
            binary_data = base64.b64decode(attachment_data[0]['datas'])
        except Exception as e:
            return f"Error decoding binary data: {str(e)}"
        
        # Langkah 4: Parse content berdasarkan mimetype
        mimetype = document.get('mimetype', '')
        extracted_text = ""
        
        try:
            if 'pdf' in mimetype.lower():
                # Proses PDF menggunakan PdfReader dari definisi di atas file
                if PdfReader is None:
                    return "Error: PDF reader library tidak tersedia. Install pypdf dengan 'pip install pypdf'"
    
                pdf_file = BytesIO(binary_data)
                pdf_reader = PdfReader(pdf_file)
                
                # Extract text from each page
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    extracted_text += page.extract_text() + "\n\n"
            
            elif 'word' in mimetype.lower() or 'docx' in mimetype.lower():
                # Proses DOCX
                if not DOCX_AVAILABLE:
                    return f"Library python-docx tidak tersedia. Silakan install dengan 'pip install python-docx'"
                
                docx_file = BytesIO(binary_data)
                doc = docx.Document(docx_file)
                
                # Extract text from paragraphs
                extracted_text = "\n\n".join([para.text for para in doc.paragraphs if para.text])
            
            else:
                return f"Tipe dokumen tidak didukung: {mimetype}"
        
        except Exception as e:
            return f"Error parsing document content: {str(e)}"
        
        # Langkah 5: Format hasil
        if not extracted_text.strip():
            return f"Dokumen ditemukan tetapi tidak ada teks yang dapat diekstrak: {document['name']}"
        
        result = f"# Dokumen: {document['name']}\n\n"
        result += f"**Tipe dokumen:** {mimetype}\n\n"
        result += f"**Isi dokumen:**\n\n{extracted_text}"
        
        return result
    except Exception as e:
        error_message = f"Error in read_document: {str(e)}"
        ctx.error(error_message)
        return error_message

# --------- PROMPTS ---------

@mcp.prompt()
def analyze_model(model: str) -> str:
    """Generate a prompt to analyze an Odoo model"""
    return f"""Please analyze the Odoo model {model}.

1. First, examine the schema to understand its structure
2. Check the number of records in the model
3. Suggest potential insights that could be gained from this data
4. Recommend some useful queries or reports for this data

Use the schema resource to help you understand the model structure and relationships."""

@mcp.prompt()
def compare_records(model: str, record_ids: List[int]) -> str:
    """Generate a prompt to compare specific records"""
    record_list = ", ".join(map(str, record_ids))
    return f"""Please compare the following records from the {model} model:
Record IDs: {record_list}

1. Fetch the records using the search_records tool with a domain like:
   search_records(
       model="{model}",
       domain=[["id", "in", {record_ids}]]
   )
2. Compare the key attributes of these records
3. Highlight significant differences
4. Identify patterns or insights from the comparison"""

@mcp.prompt()
def generate_report(report_type: str = "sales") -> str:
    """Generate a prompt for common report types"""
    
    prompts = {
        "sales": """Please generate a sales analysis report:

1. Use the run_report tool with the 'sale.order' model
2. Group by relevant dimensions (e.g., salesperson, customer, product)
3. Include measures like order total, quantity, margin if available
4. Analyze the results and identify trends or outliers
5. Provide actionable recommendations based on the findings""",
        
        "inventory": """Please generate an inventory analysis report:

1. Use the run_report tool with the 'stock.quant' model
2. Group by location, product, and category
3. Include measures for on-hand quantity and value
4. Identify potential inventory issues (low stock, excess inventory)
5. Recommend inventory optimization actions""",
        
        "financial": """Please generate a financial performance report:

1. Use the run_report tool with appropriate models (account.move, account.invoice)
2. Group by period, account, and partner
3. Include measures for debit/credit totals, balance
4. Analyze trends and variances
5. Provide financial insights and recommendations"""
    }
    
    return prompts.get(report_type, "Please specify what kind of report you'd like to generate.")

@mcp.prompt()
def analyze_document(document_name: str) -> str:
    """Generate a prompt untuk menganalisis dokumen dari sistem Odoo"""
    return f"""Silahkan analisis dokumen dengan nama "{document_name}".

1. Gunakan tool read_document untuk mendapatkan isi dokumen: 
   read_document(document_name="{document_name}")
2. Ringkas isi dokumen tersebut
3. Identifikasi poin-poin penting
4. Berikan insight tentang dokumen tersebut"""

@mcp.prompt()
def query_with_metadata(search_terms: str) -> str:
    """Generate a prompt untuk query dengan bantuan metadata"""
    return f"""Saya ingin mendapatkan data terkait "{search_terms}".

1. Gunakan tool get_contextual_metadata untuk memahami struktur data:
   get_contextual_metadata(keywords=["{search_terms}".split()])
2. Berdasarkan metadata tersebut, buatlah query yang tepat menggunakan advanced_query
3. Analisis hasilnya dan berikan insight"""

# Run the server
if __name__ == "__main__":
    mcp.run()