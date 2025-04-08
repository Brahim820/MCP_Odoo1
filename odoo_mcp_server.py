import xmlrpc.client
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from mcp.server.fastmcp import FastMCP, Context

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
    """Get schema for a specific model"""
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
    Search for records in a model
    
    Args:
        model: Odoo model name (e.g., 'res.partner')
        domain: Domain filter as a list of tuples (e.g., [['is_company', '=', True]])
        limit: Maximum number of records to return
        fields: List of fields to fetch (if empty, returns all fields)
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
    Run a simple aggregation report on model data
    
    Args:
        model: Odoo model name (e.g., 'sale.order')
        report_name: Name for this report
        domain: Domain filter as a list of tuples (optional)
        group_by: Fields to group by
        measures: Fields to aggregate (count, sum, avg)
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

1. Fetch the records using the search_records tool
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

# Run the server
if __name__ == "__main__":
    mcp.run()