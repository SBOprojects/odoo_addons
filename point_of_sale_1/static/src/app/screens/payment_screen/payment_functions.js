
// kad_shahd
export async function sendTransactionRequest(amount, vuid, api_key, tranType, public_api_key) {
    const payload = {
        "jsonrpc": "2.0",
        "method": "doTransaction",
        "id": "0883012",
        "params": [
            "ashrait", {
                "vuid": `${vuid}`,
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

    console.log("Payload:", payload);
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



// kad_shahd
export async function sendTransactionPhase1(amount, vuid, api_key, tranType, public_api_key , payments , creditTerms) {
    const payload = {
        "jsonrpc":"2.0",
        "method":"doTransactionPhase1",
        "id":"67575",
        "params": [
            "ashrait",{
                "vuid": vuid,
                "tranType": tranType,
                "tranCode": 1,
                "creditTerms": creditTerms,
                "amount": amount,
                "payments":payments,
                "currency": "376",

                }
            ]
    }
    
    console.log("Payload:", payload);
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


// kad_shahd
export async function sendTransactionPhase2(vuid, api_key, public_api_key , payments , creditTerms ) {
    const payload = {
        "jsonrpc": "2.0",
        "method": "doTransactionPhase2",
        "params": [
            "ashrait",
            {
                "vuid": vuid,
                "payments":payments,
                "creditTerms": creditTerms

            }
        ],
        "id": "952550747"
    }
    
    console.log("Payload:", payload);
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


// kad_shahd
export async function sendDoPeriodic(public_api_key,api_key) {
    const payload ={
        "jsonrpc": "2.0",
        "method": "doPeriodic",
        "params": [
            "ashrait", "wide",
            {
                "forceUpdateParams": true
            }
        ],
        "id": 2
    }
    
    console.log("Payload:", payload);
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




