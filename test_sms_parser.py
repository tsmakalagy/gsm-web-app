from datetime import datetime
import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_sms(sms_text):
    """
    Parse MVola SMS with support for both French and Malagasy formats.
    """
    # Define patterns for both languages
    french_pattern = r"""
        ^(?P<amount>\d+(?:\s*\d+)*)\s*Ar\s*    # Amount with optional spaces
        recu\s+de\s+                           # Transaction indicator (French)
        (?P<name>[^(]+)                        # Name (everything until opening parenthesis)
        \((?P<phone>\d+)\)\s*                  # Phone number in parentheses
        le\s+
        (?P<day>\d{2})/(?P<month>\d{2})/(?P<year>\d{2})\s*  # Date
        a\s+(?P<hour>\d{2}):(?P<minute>\d{2})   # Time
        .*?                                    # Non-greedy match for optional reason/server text
        Solde\s*:\s*                          # Balance indicator
        (?P<balance>\d+(?:\s*\d+)*)\s*Ar      # Balance amount
        .*?                                    # Non-greedy match for any text
        Ref:\s*(?P<reference>\d+)             # Reference number
        """

    malagasy_pattern = r"""
        ^Nahazo\s+                            # Transaction indicator (Malagasy)
        (?P<amount>\d+(?:\s*\d+)*)\s*Ar\s*    # Amount
        avy\s+any\s+amin['']ny\s+             # From indicator
        (?P<name>[^(]+)                        # Name
        \((?P<phone>\d+)\)\s*                  # Phone number
        ny\s+
        (?P<day>\d{2})/(?P<month>\d{2})/(?P<year>\d{2})\s+  # Date
        (?P<hour>\d{2}):(?P<minute>\d{2})      # Time
        .*?                                    # Non-greedy match for reason
        Ny\s+volanao\s+dia\s+                 # Balance indicator
        (?P<balance>\d+(?:\s*\d+)*)\s*Ar      # Balance
        .*?                                    # Non-greedy match
        Ref:\s*(?P<reference>\d+)             # Reference
        """

    logger.info("Attempting to parse SMS: %s", sms_text)
    
    # Try French pattern first, then Malagasy
    match = re.search(french_pattern, sms_text, re.VERBOSE | re.IGNORECASE)
    if not match:
        match = re.search(malagasy_pattern, sms_text, re.VERBOSE | re.IGNORECASE)
    
    if match:
        try:
            # Extract all matched groups as a dictionary
            result = match.groupdict()
            
            # Clean up amounts by removing spaces
            for key in ['amount', 'balance']:
                if result.get(key):
                    result[key] = re.sub(r'(\d)\s+(\d)', r'\1\2', result[key])
                    result[key] = int(result[key])  # Convert to integer
            
            # Format datetime
            date_str = "{}-{}-{} {}:{}:00".format(
                result['year'], result['month'], result['day'],
                result['hour'], result['minute']
            )
            date_obj = datetime.strptime(date_str, '%y-%m-%d %H:%M:%S')
            result['date'] = date_obj.strftime('%Y-%m-%d %H:%M:%S')
            
            # Clean up the result by removing individual date/time components
            for key in ['day', 'month', 'year', 'hour', 'minute']:
                result.pop(key, None)
            
            # Add additional information
            result.update({
                'type': 'in',  # All examples are incoming transactions
                'correspondent_type': 'Remitter',
                'raw_message': sms_text
            })
            
            logger.info("Successfully parsed: %s", result)
            return result
            
        except Exception as e:
            logger.error("Error parsing matched groups: %s", str(e))
            return None
    else:
        logger.info("No match found for SMS")
        return None

def test_sms_parser():
    """Test the SMS parser with real message formats."""
    test_messages = [
        "850 000 Ar recu de Going Beyond (0345755747) le 02/01/25 a 09:42. Serveur. Solde : 1 414 155 Ar. Ref: 544640999 Avec MVola Epargne, profitez d'un taux d'interet de 4 pourcent/an. Faites un depot des 100 Ar et epargnez jusqu'a 100 000 000 Ar. Tapez le #111*1*3*1#",
        "50 000 Ar recu de herimampianina (0346449569) le 01/08/24 a 07:44. Raison: fff. Solde : 59 950 Ar. Ref: 276567871 Avec MVola Epargne, profitez d'un taux d'interet de 4 pourcent/an. Faites un depot des 100 Ar et epargnez jusqu'a 100 000 000 Ar. Tapez le #111*1*3*1#",
        "3 477 432 Ar recu de David (0340245048) le 06/01/25 a 16:15. Raison: Tsiky nature. Solde : 4 617 637 Ar. Ref: 720662601 Avec MVola Epargne, profitez d'un taux d'interet de 4 pourcent/an. Faites un depot des 100 Ar et epargnez jusqu'a 100 000 000 Ar. Tapez le #111*1*3*1#",
        "Nahazo 100 000 Ar avy any amin'ny Herimampianina Fanimezantsoa (0341097002) ny 11/11/24 11:11. Antony: Fano.Ny volanao dia 130 992 Ar. Ref: 337304520",
        "Nahazo 109 400 Ar avy any amin'ny ANDRYHERIZO (0340691917) ny 10/09/24 12:09. Antony: vtm.Ny volanao dia 218 484 Ar. Ref: 1870942380"
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
            for key, value in sorted(result.items()):
                print("  {}: {}".format(key, value))
        else:
            print("✗ Failed to parse")
        print("-"*20)

    print("\nTesting Complete\n" + "="*50)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    test_sms_parser()