"""
Builds the "Race Pack Collection Details" email — the branded HTML
(and a plain-text fallback) for one registration, logo and all.

Kept separate from tasks.py so the content itself (wording, styling) can
be read/edited without wading through Celery/task plumbing.
"""

import base64
from pathlib import Path

SUBJECT = "Copperbelt Marathon 2026 — Race Pack Collection Details"

_LOGO_PATH = Path(__file__).parent / "assets" / "race_pack_logo.png"
_LOGO_B64 = base64.b64encode(_LOGO_PATH.read_bytes()).decode("ascii")

_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Copperbelt Marathon 2026 — Race Pack Collection</title>
</head>
<body style="margin:0; padding:0; background-color:#f3ede6; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
<div style="display:none; max-height:0; overflow:hidden; opacity:0;">
  Race pack collection details for Copperbelt Marathon 2026 — 8th &amp; 9th October at ECL Mall, Kitwe.
</div>

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f3ede6;">
  <tr>
    <td align="center" style="padding:32px 16px;">

      <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:600px; max-width:600px; background-color:#ffffff; border-radius:14px; overflow:hidden; box-shadow:0 4px 24px rgba(116,55,27,0.12);">

        <tr>
          <td align="center" style="background:linear-gradient(135deg,#1a1108 0%,#3a2210 45%,#74371B 100%); padding:36px 24px 28px;">
            <img src="data:image/png;base64,{logo_b64}" width="110" alt="Copperbelt Marathon 2026" style="display:block; margin:0 auto 14px; width:110px; height:auto;" />
            <div style="font-size:22px; line-height:1.3; font-weight:800; letter-spacing:0.08em; color:#F4EFE9; text-transform:uppercase;">Copperbelt Marathon</div>
            <div style="font-size:13px; letter-spacing:0.3em; color:#D6A855; text-transform:uppercase; margin-top:4px;">10 October 2026</div>
          </td>
        </tr>

        <tr>
          <td style="background-color:#D6A855; padding:10px 24px; text-align:center;">
            <span style="font-size:13px; font-weight:700; letter-spacing:0.05em; color:#1A1108; text-transform:uppercase;">Race Pack Collection Details</span>
          </td>
        </tr>

        <tr>
          <td style="padding:32px 32px 8px;">
            <p style="margin:0 0 18px; font-size:16px; line-height:1.6; color:#2a1d14;">Dear <strong>{first_name}</strong>,</p>
            <p style="margin:0 0 24px; font-size:15px; line-height:1.7; color:#44362b;">Please see the race pack collection details below ahead of race day.</p>
          </td>
        </tr>

        <tr>
          <td style="padding:0 32px;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="padding:14px 16px; background-color:#faf6f0; border-left:4px solid #C06A38; border-radius:6px;">
                  <span style="font-size:13px; font-weight:700; color:#74371B; text-transform:uppercase; letter-spacing:0.03em;">Corporate Collections</span><br/>
                  <span style="font-size:14px; color:#44362b; line-height:1.6;">We shall deliver.</span>
                </td>
              </tr>
              <tr><td style="height:12px; line-height:12px; font-size:0;">&nbsp;</td></tr>
              <tr>
                <td style="padding:14px 16px; background-color:#faf6f0; border-left:4px solid #C06A38; border-radius:6px;">
                  <span style="font-size:13px; font-weight:700; color:#74371B; text-transform:uppercase; letter-spacing:0.03em;">Virtual Participants</span><br/>
                  <span style="font-size:14px; color:#44362b; line-height:1.6;">Race packs will be sent.</span>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <tr>
          <td style="padding:24px 32px 0;">
            <div style="font-size:13px; font-weight:700; color:#74371B; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:10px;">Individual Collections</div>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #ecdfd0; border-radius:8px; overflow:hidden;">
              <tr>
                <td style="padding:14px 16px; border-bottom:1px solid #ecdfd0;">
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
                    <td style="font-size:14.5px; font-weight:600; color:#2a1d14;">8th October (Thursday)</td>
                    <td align="right" style="font-size:14.5px; font-weight:700; color:#C06A38;">09:00 &ndash; 17:00</td>
                  </tr></table>
                </td>
              </tr>
              <tr>
                <td style="padding:14px 16px;">
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
                    <td style="font-size:14.5px; font-weight:600; color:#2a1d14;">9th October (Friday)</td>
                    <td align="right" style="font-size:14.5px; font-weight:700; color:#C06A38;">09:00 &ndash; 17:00</td>
                  </tr></table>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <tr>
          <td style="padding:20px 32px 0;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#1a1108; border-radius:8px;">
              <tr>
                <td style="padding:16px 18px;">
                  <span style="font-size:11px; font-weight:700; color:#D6A855; text-transform:uppercase; letter-spacing:0.08em;">Venue</span><br/>
                  <span style="font-size:15px; font-weight:600; color:#F4EFE9; line-height:1.5;">ECL Mall, Kitwe &mdash; Marathon Registration Desk</span>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <tr>
          <td style="padding:20px 32px 0;">
            <p style="margin:0; font-size:14.5px; line-height:1.7; color:#44362b;">
              Please come with your Marathon Registration Number
              (<strong style="color:#74371B;">{reference}</strong>) for collection.
            </p>
          </td>
        </tr>

        <tr>
          <td style="padding:18px 32px 0;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#fdeeea; border:1px solid #f3c6b8; border-radius:8px;">
              <tr>
                <td style="padding:14px 18px; text-align:center;">
                  <span style="font-size:15px; font-weight:800; color:#b5432b; letter-spacing:0.02em;">&#9888;&#65039; NO BIB, NO MEDAL</span>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <tr>
          <td style="padding:28px 32px 36px; text-align:center;">
            <p style="margin:0; font-size:16px; font-weight:700; color:#2a1d14;">See you on race day! &#127937;</p>
          </td>
        </tr>

        <tr>
          <td style="background-color:#f3ede6; padding:22px 32px; text-align:center; border-top:1px solid #ecdfd0;">
            <p style="margin:0 0 10px; font-size:12.5px; font-weight:700; color:#74371B; text-transform:uppercase; letter-spacing:0.05em;">Questions? Get in touch</p>
            <p style="margin:0 0 4px; font-size:13.5px; color:#44362b; line-height:1.7;">
              <a href="tel:+260764915118" style="color:#C06A38; text-decoration:none; font-weight:600;">+260 764 915 118</a>
              &nbsp;&middot;&nbsp;
              <a href="mailto:copperbeltmarathon@gmail.com" style="color:#C06A38; text-decoration:none; font-weight:600;">copperbeltmarathon@gmail.com</a>
            </p>
            <p style="margin:14px 0 0; font-size:11.5px; color:#8a7c6e; line-height:1.6;">Copperbelt Marathon 2026 &middot; 10 October 2026 &middot; Kitwe, Zambia</p>
          </td>
        </tr>

      </table>

    </td>
  </tr>
</table>
</body>
</html>
"""

_TEXT_TEMPLATE = """Dear {first_name},

Please see the 10th October - Copperbelt Marathon 2026 Race Pack Collection details below:

Corporate Collections: We Shall Deliver.

Virtual Participants: Race Packs Will Be Sent.

Individual Collections:
8th October (Thursday): 09:00hrs-17:00hrs
9th October (Friday): 09:00hrs-17:00hrs

Venue: ECL Mall, Kitwe - Marathon Registration Desk

Please come with your Marathon Registration Number ({reference}) for collection.
NO BIB, NO MEDAL.

Questions? Call +260 764 915 118 or email copperbeltmarathon@gmail.com

See you on race day!"""


def build_race_pack_email(*, first_name, reference):
    """Returns (subject, text_body, html_body) for one recipient."""
    html = _HTML_TEMPLATE.format(logo_b64=_LOGO_B64, first_name=first_name, reference=reference)
    text = _TEXT_TEMPLATE.format(first_name=first_name, reference=reference)
    return SUBJECT, text, html
