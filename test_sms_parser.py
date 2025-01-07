from datetime import datetime
import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_sms(sms):
    """Parse the SMS using regex."""
    pattern = r"(\d+\s*Ar)\s*recu\s*de\s*([^\(]+)\((\d+)\)\s*le\s*(\d{2}/\d{2}/\d{2})\s*a\s*(\d{2}:\d{2}).*?Solde\s*:\s*(\d+\s*Ar).*?Ref:\s*(\d+)"
    
    logger.info("Attempting to parse SMS: %s", sms)
    match = re.search(pattern, sms)
    
    if match:
        try:
            result = {
                "amount": int(match.group(1).replace("Ar", "").replace(" ", "")),
                "receiver": match.group(2).strip(),
                "sender": match.group(3),
                "date_time": datetime.strptime("{} {}".format(match.group(4), match.group(5)), "%d/%m/%y %H:%M"),
                "balance": int(match.group(6).replace("Ar", "").replace(" ", "")),
                "reference": match.group(7),
                "raw_message": sms
            }
            logger.info("Successfully parsed: %s", result)
            return result
        except Exception as e:
            logger.error("Error parsing matched groups: %s", str(e))
            return None
    else:
        logger.info("No match found for SMS")
        return None

def test_sms_parser():
    # Test cases
    test_messages = [
        # Regular format
        "50 000 Ar recu de herimampianina (0346449569) le 01/08/24 a 07:44. Raison: fff. Solde : 59 950 Ar. Ref: 276567871 Avec MVola Epargne...",
        
        # Different amount format
        "850 000 Ar recu de Going Beyond (0345755747) le 02/01/25 a 09:42. Serveur. Solde : 1 414 155 Ar. Ref: 544640999 Avec MVola Epargne...",
        
        # Invalid format (should fail)
        "This is not a valid SMS format",
        
        # Different spacing
        "50000Ar recu de Test User(0341234567) le 01/01/24 a 12:34. Solde:59950Ar. Ref:123456789",
        
        # With additional text in between
        "50 000 Ar recu de Test (0341234567) le 01/01/24 a 12:34. Some random text here. Solde : 59 950 Ar. More text. Ref: 123456789"
    ]

    print("\nStarting SMS Parser Tests\n" + "="*50)
    
    for i, sms in enumerate(test_messages, 1):
        print("\nTest Case #{}\n{}".format(i, "-"*20))
        print("Input SMS:")
        print(sms)
        print("\nResult:")
        result = parse_sms(sms)
        if result:
            print("✓ Successfully parsed:")
            for key, value in result.items():
                print("  {}: {}".format(key, value))
        else:
            print("✗ Failed to parse")
        print("-"*20)

    print("\nTesting Complete\n" + "="*50)

if __name__ == "__main__":
    test_sms_parser()