"""R12 — Generate /myaccount hub GUI tasks for the Booking mirror.

Emits ≥40 tasks tagged Booking--myacct_<NNN>. Tasks cover:
  - dashboard (next-trip / counts / inbox badge)
  - personal-details (read + update form)
  - preferences (language/currency/email toggles)
  - payment-methods (list + add + delete)
  - privacy (toggles)
  - security (password change + 2FA enable/disable)
  - reviews (list)
  - genius (status + points history)
  - wallet (balance + history)
  - inbox (list / detail / mark-read / reply)

Run from sites/booking/ and the file is appended to tasks.jsonl.
"""
import json
import pathlib

OUT = pathlib.Path(__file__).resolve().parent.parent / "tasks.jsonl"
WEB = "http://localhost:40005/"
UP = "https://www.booking.com/"


def t(idx, ques):
    return {
        "web_name": "Booking",
        "id": f"Booking--myacct_{idx:03d}",
        "ques": ques,
        "web": WEB,
        "upstream_url": UP,
    }


tasks = []
i = 1


def add(q):
    global i
    tasks.append(t(i, q))
    i += 1


# Dashboard ------------------------------------------------------------------
add("Sign in as sophie.m@test.com (password TestPass123!) and open /myaccount. Report the value shown for 'Total bookings'.")
add("Sign in as sophie.m@test.com (password TestPass123!) and open /myaccount. Report the wallet credit balance shown in the dashboard stats (USD).")
add("Sign in as emma.w@test.com (password TestPass123!) and open /myaccount. Report the Genius points shown in the dashboard stats.")
add("Sign in as kenji.t@test.com (password TestPass123!) and open /myaccount. Report the property name shown under 'Next trip'.")
add("Sign in as carlos.s@test.com (password TestPass123!) and open /myaccount. Report the unread message count shown on the Inbox tile.")

# Personal details -----------------------------------------------------------
add("Sign in as sophie.m@test.com (password TestPass123!), open /myaccount/personal-details, and report the current value of the Phone field.")
add("Sign in as sophie.m@test.com (password TestPass123!), open /myaccount/personal-details, change the Postal code to 75008 and save. After save, report the Postal code value shown on the page.")
add("Sign in as emma.w@test.com (password TestPass123!), open /myaccount/personal-details, change the City to Manchester and save. After save, report the City value shown on the page.")
add("Sign in as kenji.t@test.com (password TestPass123!), open /myaccount/personal-details, and verify the Email field is read-only (disabled). Report the email address shown.")

# Preferences ----------------------------------------------------------------
add("Sign in as sophie.m@test.com (password TestPass123!), open /myaccount/preferences, and report the currently selected Language option.")
add("Sign in as kenji.t@test.com (password TestPass123!), open /myaccount/preferences, and report the currently selected Currency option.")
add("Sign in as carlos.s@test.com (password TestPass123!), open /myaccount/preferences, change the Currency to USD, ensure 'Deals & promotions' email is on, then save. Report the flash message shown.")
add("Sign in as emma.w@test.com (password TestPass123!), open /myaccount/preferences, toggle 'Travel inspiration newsletter' off and save. After save, report whether the checkbox is on or off.")
add("Sign in as kenji.t@test.com (password TestPass123!), open /myaccount/preferences, and report whether the 'Deals & promotions' email toggle is currently on or off.")

# Payment methods ------------------------------------------------------------
add("Sign in as sophie.m@test.com (password TestPass123!), open /myaccount/payment-methods, and report how many saved cards are listed.")
add("Sign in as sophie.m@test.com (password TestPass123!), open /myaccount/payment-methods, and report which card brand is marked as the Default.")
add("Sign in as kenji.t@test.com (password TestPass123!), open /myaccount/payment-methods, add a new Visa ending 9999 (cardholder Kenji Tanaka, expiry 11/30, CVV 222), then report how many saved cards are listed after the add.")
add("Sign in as emma.w@test.com (password TestPass123!), open /myaccount/payment-methods, add a new Mastercard (number 5555 4444 3333 2222, cardholder Emma Williams, expiry 09/29, CVV 999), then click Remove on that card. Report how many saved cards remain.")
add("Sign in as carlos.s@test.com (password TestPass123!), open /myaccount/payment-methods, and report the last4 digits of every saved card, comma-separated.")

# Privacy --------------------------------------------------------------------
add("Sign in as sophie.m@test.com (password TestPass123!), open /myaccount/privacy, and report whether the 'Personalised advertising' toggle is on or off.")
add("Sign in as kenji.t@test.com (password TestPass123!), open /myaccount/privacy, turn 'Personalised advertising' on, save, then report the flash message shown.")
add("Sign in as carlos.s@test.com (password TestPass123!), open /myaccount/privacy, and report whether 'Share my data with hotel partners' is on or off.")

# Security -------------------------------------------------------------------
add("Sign in as sophie.m@test.com (password TestPass123!), open /myaccount/security, and report whether two-factor authentication is currently enabled.")
add("Sign in as sophie.m@test.com (password TestPass123!), open /myaccount/security, and report which 2FA method (sms / authenticator / email) is currently in use.")
add("Sign in as kenji.t@test.com (password TestPass123!), open /myaccount/security, enable two-factor authentication using SMS as the method, then report the flash message shown.")
add("Sign in as emma.w@test.com (password TestPass123!), open /myaccount/security, disable two-factor authentication, then report the flash message shown.")
add("Sign in as carlos.s@test.com (password TestPass123!), open /myaccount/security, change the password from TestPass123! to NewPass456! and report the flash message. Then change it back to TestPass123!.")
add("Sign in as sophie.m@test.com (password TestPass123!), open /myaccount/security, attempt to change the password using the WRONG current password 'wrong123' and a new password 'NewPass456!'. Report the error message shown.")

# Reviews --------------------------------------------------------------------
add("Sign in as sophie.m@test.com (password TestPass123!), open /myaccount/reviews, and report how many reviews are listed (0 if none).")
add("Sign in as sophie.m@test.com (password TestPass123!), open /myaccount/reviews, and report whether the page shows an empty-state message when there are no reviews.")

# Genius ---------------------------------------------------------------------
add("Sign in as sophie.m@test.com (password TestPass123!), open /myaccount/genius, and report her current Genius level number (1 / 2 / 3).")
add("Sign in as sophie.m@test.com (password TestPass123!), open /myaccount/genius, and report her current Genius points total.")
add("Sign in as kenji.t@test.com (password TestPass123!), open /myaccount/genius, and report how many points he needs to reach the next tier.")
add("Sign in as emma.w@test.com (password TestPass123!), open /myaccount/genius, and report how many entries appear in the 'Points history' table.")
add("Sign in as carlos.s@test.com (password TestPass123!), open /myaccount/genius, and report the description text of the most recent EARN event in the history table.")

# Wallet ---------------------------------------------------------------------
add("Sign in as sophie.m@test.com (password TestPass123!), open /myaccount/wallet, and report her available balance in USD.")
add("Sign in as carlos.s@test.com (password TestPass123!), open /myaccount/wallet, and report the total number of transactions listed in the history table.")
add("Sign in as emma.w@test.com (password TestPass123!), open /myaccount/wallet, and report the description of the CASHBACK transaction.")
add("Sign in as kenji.t@test.com (password TestPass123!), open /myaccount/wallet, and report his welcome-bonus credit amount in USD.")

# Inbox ----------------------------------------------------------------------
add("Sign in as sophie.m@test.com (password TestPass123!), open /myaccount/inbox, and report how many total messages are listed.")
add("Sign in as sophie.m@test.com (password TestPass123!), open /myaccount/inbox, and report the subject line of the unread PROPERTY_REPLY message.")
add("Sign in as kenji.t@test.com (password TestPass123!), open /myaccount/inbox, click the first PROPERTY_REPLY message to open it, and report the sender shown in the detail view.")
add("Sign in as carlos.s@test.com (password TestPass123!), open /myaccount/inbox, find the unread PROPERTY_REPLY from Faena Hotel Miami Beach, click 'Mark read' on it, and report the flash message shown.")
add("Sign in as emma.w@test.com (password TestPass123!), open /myaccount/inbox, open the property reply from The Ned London, submit a reply with body 'Thank you, we will bring a cot.' and report the flash message shown.")
add("Sign in as sophie.m@test.com (password TestPass123!), open /myaccount/inbox, and report how many UNREAD messages appear (the badge count in the sidebar).")
add("Sign in as carlos.s@test.com (password TestPass123!), open /myaccount/inbox, and report the kind of the most recent message (property_reply / promo / system / booking_update).")

# Sidebar nav consistency ----------------------------------------------------
add("Sign in as sophie.m@test.com (password TestPass123!), open /myaccount/preferences, and verify that the left sidebar lists at least the links: Dashboard, Personal details, Preferences, Payment methods, Privacy, Security, My reviews, Genius loyalty, Wallet, Inbox. Report the link that is highlighted as the current page.")
add("Sign in as kenji.t@test.com (password TestPass123!) and visit /myaccount/wallet. From the sidebar, click 'Genius loyalty' and report the URL of the destination page.")

assert len(tasks) >= 40, f"only {len(tasks)} tasks"
print(f"generated {len(tasks)} tasks")

with open(OUT, "a") as f:
    for tk in tasks:
        f.write(json.dumps(tk, ensure_ascii=False) + "\n")
print(f"appended to {OUT}")
