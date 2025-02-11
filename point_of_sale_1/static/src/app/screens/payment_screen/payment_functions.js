
// kad_shahd
export async function sendTransactionRequest(amount, vuid, api_key, tranType, public_api_key) {
    const payload = {
        "jsonrpc": "2.0",
        "method": "doTransaction",
        "id": "0883012",
        "params": [
            "ashrait", {
                "vuid": vuid,
                "tranType": tranType,
                "tranCode": 1,
                "creditTerms": 1,
                "amount": amount,
                "currency": "376",
                "additionalInfo": {
                    "storeId": "string",
                    "posId": "string"
                }
            }
        ]
    }

    // Send the request
    const url = `https://${public_api_key}:8443/SPICy/`;

    try {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "id": api_key,
            },
            body: JSON.stringify(payload),
        });

        const result = await response.json();
        console.log("Response:", result);
        return result; // Return the response for further processing if needed
    } catch (error) {
        console.error("Error during the transaction:", error);
    }
}
