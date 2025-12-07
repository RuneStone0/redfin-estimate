from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import httpx
import json
import re
from typing import Optional

app = FastAPI(
    title="Redfin API Bridge",
    description="API to fetch property data from Redfin",
    version="1.0.0"
)


def parse_redfin_response(response_text: str) -> dict:
    """
    Parse Redfin's malformed JSON response that starts with {}&&
    Also handles JSON embedded in HTML (e.g., in script tags)
    """
    # First, try to find JSON in script tags (common pattern for embedded data)
    script_pattern = r'<script[^>]*>.*?(\{.*?\})</script>'
    script_matches = re.findall(script_pattern, response_text, re.DOTALL)
    
    # Try to find the malformed JSON pattern {}&&{...}
    malformed_json_pattern = r'\{\}&&(\{.*\})'
    malformed_match = re.search(malformed_json_pattern, response_text, re.DOTALL)
    
    # Try direct JSON parsing if it starts with {}&&
    cleaned_text = re.sub(r'^\{?\}?&&', '', response_text.strip())
    
    # Try parsing in order of preference
    for text_to_parse in [malformed_match.group(1) if malformed_match else None,
                          cleaned_text if cleaned_text.startswith('{') else None,
                          *script_matches]:
        if text_to_parse:
            try:
                return json.loads(text_to_parse)
            except (json.JSONDecodeError, AttributeError):
                continue
    
    # If nothing worked, try to extract any JSON-like structure
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    json_matches = re.findall(json_pattern, response_text)
    for match in json_matches:
        try:
            parsed = json.loads(match)
            if "payload" in parsed or "avmInfo" in parsed:
                return parsed
        except json.JSONDecodeError:
            continue
    
    raise ValueError("Could not find valid JSON in response")


async def fetch_property_data(propertyId: int) -> dict:
    """
    Shared function to fetch property data from Redfin API
    
    - **propertyId**: The Redfin property ID
    
    Returns the property data dictionary (payload if available, otherwise full response)
    """
    # Headers to make the request look like it's coming from a browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://www.redfin.com/",
        "Origin": "https://www.redfin.com",
    }
    
    # Try multiple potential API endpoints
    api_endpoints = [
        f"https://www.redfin.com/stingray/api/home/details/avm?propertyId={propertyId}&accessLevel=1",
        f"https://www.redfin.com/stingray/do/api-details?propertyId={propertyId}",
        f"https://www.redfin.com/what-is-my-home-worth?propertyId={propertyId}",
    ]
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        last_error = None
        
        for url in api_endpoints:
            try:
                response = await client.get(url, headers=headers)
                
                # If we get a redirect, continue to next endpoint
                if response.status_code == 302:
                    continue
                
                response.raise_for_status()
                
                # Try to parse the response
                try:
                    parsed_data = parse_redfin_response(response.text)
                    
                    # Return the payload if it exists, otherwise return the entire response
                    if "payload" in parsed_data:
                        return parsed_data["payload"]
                    else:
                        return parsed_data
                except ValueError as parse_error:
                    # If parsing fails, try next endpoint
                    last_error = parse_error
                    continue
                    
            except httpx.HTTPStatusError as e:
                # If this endpoint fails, try the next one
                last_error = e
                continue
        
        # If all endpoints failed, raise an error
        if last_error:
            if isinstance(last_error, httpx.HTTPStatusError):
                raise HTTPException(
                    status_code=last_error.response.status_code,
                    detail=f"Redfin API returned error: {last_error.response.status_code}. All attempted endpoints failed."
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to parse response from any endpoint: {str(last_error)}"
                )
        else:
            raise HTTPException(
                status_code=503,
                detail="All Redfin API endpoints returned redirects or failed"
            )


@app.get("/api/property")
async def get_property_estimate(propertyId: int = Query(..., description="Redfin property ID")):
    """
    Fetch property estimate from Redfin API
    
    - **propertyId**: The Redfin property ID (e.g., 109913415)
    
    Returns the extracted JSON payload from Redfin's response.
    """
    try:
        property_data = await fetch_property_data(propertyId)
        return JSONResponse(content=property_data)
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Redfin API returned error: {e.response.status_code}"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to Redfin API: {str(e)}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse response: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


def find_predicted_value(data: dict, path: str = "") -> tuple:
    """
    Recursively search for predictedValue in the data structure.
    Returns (value, path) if found, (None, None) otherwise.
    """
    if isinstance(data, dict):
        # Check if predictedValue is directly in this dict
        if "predictedValue" in data:
            return (data["predictedValue"], path + ".predictedValue" if path else "predictedValue")
        
        # Check common locations
        if "avmInfo" in data and isinstance(data["avmInfo"], dict):
            if "predictedValue" in data["avmInfo"]:
                return (data["avmInfo"]["predictedValue"], (path + ".avmInfo.predictedValue" if path else "avmInfo.predictedValue"))
        
        # Recursively search in nested dictionaries
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                result = find_predicted_value(value, path + "." + key if path else key)
                if result[0] is not None:
                    return result
    
    elif isinstance(data, list):
        # Search in list items
        for i, item in enumerate(data):
            if isinstance(item, (dict, list)):
                result = find_predicted_value(item, path + f"[{i}]")
                if result[0] is not None:
                    return result
    
    return (None, None)


@app.get("/api/property/value")
async def get_property_value(propertyId: int = Query(..., description="Redfin property ID")):
    """
    Fetch predicted property value from Redfin API
    
    - **propertyId**: The Redfin property ID (e.g., 109913415)
    
    Returns only the predictedValue from the property data.
    """
    try:
        property_data = await fetch_property_data(propertyId)
        
        # Search for predictedValue in the data structure
        predicted_value, found_path = find_predicted_value(property_data)
        
        if predicted_value is not None:
            return JSONResponse(content={"predictedValue": predicted_value})
        else:
            # Provide more helpful error message with available keys
            available_keys = list(property_data.keys()) if isinstance(property_data, dict) else []
            raise HTTPException(
                status_code=404,
                detail=f"predictedValue not found in property data. Available top-level keys: {available_keys}"
            )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Redfin API returned error: {e.response.status_code}"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to Redfin API: {str(e)}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse response: {str(e)}"
        )
    except HTTPException:
        # Re-raise HTTPExceptions (like the 404 above)
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


@app.get("/")
async def root():
    """
    Root endpoint with API information
    """
    return {
        "message": "Redfin API Bridge",
        "docs": "/docs",
        "endpoints": {
            "property": "/api/property?propertyId=<property_id>",
            "value": "/api/property/value?propertyId=<property_id>"
        }
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy"}

