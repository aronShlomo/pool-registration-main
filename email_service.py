import resend

from config import Config


# ============================================================
# RESEND CONFIGURATION
# ============================================================

resend.api_key = Config.RESEND_API_KEY


# ============================================================
# BASIC EMAIL SENDER
# ============================================================

def send_email(to, subject, html):
    """
    Send an HTML email through Resend.
    """

    if not Config.RESEND_API_KEY:
        raise RuntimeError(
            "RESEND_API_KEY is not configured."
        )

    if not Config.EMAIL_FROM:
        raise RuntimeError(
            "EMAIL_FROM is not configured."
        )

    if not to:
        raise RuntimeError(
            "Recipient email is missing."
        )

    recipient = str(to).strip()

    params = {
        "from": Config.EMAIL_FROM,
        "to": [recipient],
        "subject": subject,
        "html": html
    }

    print("========================================")
    print("RESEND EMAIL SEND")
    print("FROM:", Config.EMAIL_FROM)
    print("TO:", recipient)
    print("SUBJECT:", subject)
    print("========================================")

    response = resend.Emails.send(params)

    print(
        "RESEND RESPONSE:",
        repr(response)
    )

    return response


# ============================================================
# FRIENDLY PRICE
# ============================================================

def friendly_price(price):
    """
    Make sure the price displays with a dollar sign.
    """

    if price is None:
        return "Not available"

    price = str(price).strip()

    if not price:
        return "Not available"

    if price.startswith("$"):
        return price

    return f"${price}"


# ============================================================
# OWNER — NEW REGISTRATION REQUEST
# ============================================================

def send_admin_notification(booking):
    """
    Send the owner a new booking request.

    Pending:
        Approve / Reject

    Confirmed + paid:
        Payment notification

    Confirmed + Pay Later:
        Pay Later notification
    """

    booking = dict(booking)

    booking_id = booking.get("id")

    name = booking.get(
        "name",
        booking.get("student_name", "Student")
    )

    email = booking.get(
        "email",
        ""
    )

    phone = booking.get(
        "phone",
        ""
    )

    lesson_type = booking.get(
        "lesson_type",
        ""
    )

    package = booking.get(
        "package",
        ""
    )

    lesson_date = booking.get(
        "lesson_date",
        ""
    )

    lesson_time = booking.get(
        "lesson_time",
        ""
    )

    price = friendly_price(
        booking.get("price")
    )

    status = booking.get(
        "status",
        "pending"
    )

    payment_status = booking.get(
        "payment_status",
        "pending"
    )

    payment_method = booking.get(
        "payment_method",
        "not_selected"
    )

    approval_token = str(
        booking.get(
            "approval_token",
            ""
        ) or ""
    ).strip()


    # ========================================================
    # PENDING — OWNER NEEDS TO APPROVE
    # ========================================================

    if status == "pending":

        if not approval_token:

            raise RuntimeError(
                "Approval token is missing from booking."
            )


        # ----------------------------------------------------
        # CLEAN DOMAIN
        # ----------------------------------------------------

        domain = str(
            Config.DOMAIN or ""
        ).strip().rstrip("/")


        if not domain:

            raise RuntimeError(
                "DOMAIN is not configured."
            )


        # ----------------------------------------------------
        # APPROVAL URL
        # ----------------------------------------------------

        approve_url = (
            f"{domain}"
            f"/api/approve-booking"
            f"?token={approval_token}"
        )


        # ----------------------------------------------------
        # REJECTION URL
        # ----------------------------------------------------

        reject_url = (
            f"{domain}"
            f"/api/reject-booking"
            f"?token={approval_token}"
        )


        print("========================================")
        print("OWNER APPROVAL EMAIL")
        print("BOOKING ID:", booking_id)
        print(
            "OWNER EMAIL:",
            Config.OWNER_EMAIL
        )
        print(
            "APPROVAL TOKEN PRESENT:",
            bool(approval_token)
        )
        print(
            "APPROVE URL:",
            approve_url
        )
        print(
            "REJECT URL:",
            reject_url
        )
        print("========================================")


        subject = (
            f"New Lesson Request — {name}"
        )


        # ----------------------------------------------------
        # OWNER EMAIL
        # ----------------------------------------------------

        html = f"""
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>
Millrod Swim Academy - New Booking
</title>

</head>


<body style="
    margin:0;
    padding:0;
    background:#eef7fb;
    font-family:Arial,Helvetica,sans-serif;
    color:#263238;
">


<div style="
    max-width:680px;
    margin:30px auto;
    padding:20px;
">


    <!-- =====================================================
         MAIN CARD
    ====================================================== -->

    <div style="
        background:#ffffff;
        border-radius:20px;
        overflow:hidden;
        box-shadow:0 10px 35px rgba(0,0,0,0.10);
    ">


        <!-- =================================================
             HEADER
        ================================================== -->

        <div style="
            background:linear-gradient(
                135deg,
                #0077b6,
                #023e8a
            );
            padding:35px 25px;
            text-align:center;
            color:#ffffff;
        ">

            <div style="
                font-size:45px;
                margin-bottom:10px;
            ">
                🏊
            </div>


            <h1 style="
                margin:0;
                font-size:27px;
                font-weight:700;
            ">
                New Lesson Request
            </h1>


            <p style="
                margin:10px 0 0;
                font-size:15px;
                opacity:0.92;
            ">
                Millrod Swim Academy
            </p>

        </div>


        <!-- =================================================
             CONTENT
        ================================================== -->

        <div style="
            padding:35px;
        ">


            <p style="
                font-size:17px;
                line-height:1.6;
                margin-top:0;
            ">

                A new swimming lesson registration
                is waiting for your review.

            </p>


            <!-- =============================================
                 BOOKING DETAILS
            ============================================== -->

            <div style="
                background:#f6fbfe;
                border:1px solid #dceef7;
                border-radius:14px;
                padding:24px;
                margin:25px 0;
            ">


                <h2 style="
                    margin:0 0 18px;
                    color:#023e8a;
                    font-size:20px;
                ">

                    Booking Details

                </h2>


                <p style="
                    margin:9px 0;
                ">
                    <strong>Student:</strong>
                    {name}
                </p>


                <p style="
                    margin:9px 0;
                ">
                    <strong>Email:</strong>
                    {email}
                </p>


                <p style="
                    margin:9px 0;
                ">
                    <strong>Phone:</strong>
                    {phone}
                </p>


                <p style="
                    margin:9px 0;
                ">
                    <strong>Lesson:</strong>
                    {lesson_type}
                </p>


                <p style="
                    margin:9px 0;
                ">
                    <strong>Package:</strong>
                    {package}
                </p>


                <p style="
                    margin:9px 0;
                ">
                    <strong>Date:</strong>
                    {lesson_date}
                </p>


                <p style="
                    margin:9px 0;
                ">
                    <strong>Time:</strong>
                    {lesson_time}
                </p>


                <p style="
                    margin:9px 0 0;
                ">
                    <strong>Amount:</strong>
                    {price}
                </p>


            </div>


            <!-- =============================================
                 ACTION MESSAGE
            ============================================== -->

            <div style="
                text-align:center;
                margin:30px 0 20px;
            ">

                <h2 style="
                    margin:0 0 10px;
                    color:#023e8a;
                    font-size:21px;
                ">

                    Review This Booking

                </h2>


                <p style="
                    color:#666666;
                    line-height:1.5;
                    margin:0;
                ">

                    Please approve or reject this
                    lesson request.

                </p>

            </div>


            <!-- =============================================
                 APPROVE BUTTON
            ============================================== -->

            <div style="
                text-align:center;
                margin:25px 0 12px;
            ">

                <a
                    href="{approve_url}"
                    target="_blank"
                    style="
                        display:inline-block;
                        background:#198754;
                        color:#ffffff;
                        padding:17px 34px;
                        border-radius:10px;
                        text-decoration:none;
                        font-size:17px;
                        font-weight:bold;
                        border:1px solid #198754;
                    "
                >

                    ✔ Approve Booking

                </a>

            </div>


            <!-- =============================================
                 REJECT BUTTON
            ============================================== -->

            <div style="
                text-align:center;
                margin:10px 0 25px;
            ">

                <a
                    href="{reject_url}"
                    target="_blank"
                    style="
                        display:inline-block;
                        background:#dc3545;
                        color:#ffffff;
                        padding:14px 30px;
                        border-radius:10px;
                        text-decoration:none;
                        font-size:16px;
                        font-weight:bold;
                        border:1px solid #dc3545;
                    "
                >

                    ✖ Reject Booking

                </a>

            </div>


            <!-- =============================================
                 BACKUP APPROVAL LINK
            ============================================== -->

            <div style="
                margin-top:30px;
                padding:22px;
                background:#f8fafc;
                border:1px solid #dce5eb;
                border-radius:12px;
            ">


                <p style="
                    margin:0 0 12px;
                    text-align:center;
                    color:#555555;
                    font-size:14px;
                    font-weight:bold;
                ">

                    If the Approve button does not work,
                    use this link:

                </p>


                <p style="
                    margin:0;
                    text-align:center;
                    word-break:break-all;
                    line-height:1.6;
                    font-size:13px;
                ">

                    <a
                        href="{approve_url}"
                        target="_blank"
                        style="
                            color:#0077b6;
                            text-decoration:underline;
                        "
                    >
                        {approve_url}
                    </a>

                </p>

            </div>


            <!-- =============================================
                 BACKUP REJECT LINK
            ============================================== -->

            <div style="
                margin-top:15px;
                padding:18px;
                background:#fff8f8;
                border:1px solid #f0d6d6;
                border-radius:12px;
            ">


                <p style="
                    margin:0 0 10px;
                    text-align:center;
                    color:#666666;
                    font-size:13px;
                ">

                    Reject link:

                </p>


                <p style="
                    margin:0;
                    text-align:center;
                    word-break:break-all;
                    font-size:13px;
                    line-height:1.6;
                ">

                    <a
                        href="{reject_url}"
                        target="_blank"
                        style="
                            color:#dc3545;
                            text-decoration:underline;
                        "
                    >
                        {reject_url}
                    </a>

                </p>

            </div>


            <!-- =============================================
                 BOOKING ID
            ============================================== -->

            <div style="
                margin-top:25px;
                text-align:center;
                color:#888888;
                font-size:12px;
            ">

                Booking ID:
                <strong>
                    #{booking_id}
                </strong>

            </div>


        </div>


        <!-- =================================================
             FOOTER
        ================================================== -->

        <div style="
            background:#f5f8fa;
            padding:22px;
            text-align:center;
            color:#777777;
            font-size:13px;
        ">

            <strong>
                Millrod Swim Academy
            </strong>

            <br>

            Professional Swimming Lessons

        </div>


    </div>


</div>


</body>

</html>
"""


        return send_email(
            Config.OWNER_EMAIL,
            subject,
            html
        )


    # ========================================================
    # CONFIRMED + PAID
    # ========================================================

    if (
        status == "confirmed"
        and payment_status == "paid"
    ):

        subject = (
            f"Payment Received — Booking #{booking_id}"
        )


        html = f"""
<!DOCTYPE html>

<html>

<body style="
    margin:0;
    padding:0;
    background:#f4f8fb;
    font-family:Arial,Helvetica,sans-serif;
">

<div style="
    max-width:620px;
    margin:30px auto;
    padding:20px;
">

<div style="
    background:#ffffff;
    border-radius:18px;
    padding:35px;
    box-shadow:0 8px 30px rgba(0,0,0,.08);
">

<h2 style="
    color:#198754;
    text-align:center;
">

    💳 Payment Received

</h2>


<p>

    Booking
    <strong>#{booking_id}</strong>
    has been paid successfully.

</p>


<div style="
    background:#f6fbfe;
    padding:20px;
    border-radius:12px;
    margin:20px 0;
">

<p>
<strong>Student:</strong>
{name}
</p>

<p>
<strong>Lesson:</strong>
{lesson_type}
</p>

<p>
<strong>Package:</strong>
{package}
</p>

<p>
<strong>Date:</strong>
{lesson_date}
</p>

<p>
<strong>Time:</strong>
{lesson_time}
</p>

<p>
<strong>Amount:</strong>
{price}
</p>

</div>


<p style="
    color:#198754;
    font-weight:bold;
">

Payment status: PAID

</p>


</div>

</div>

</body>

</html>
"""


        return send_email(
            Config.OWNER_EMAIL,
            subject,
            html
        )


    # ========================================================
    # CONFIRMED + PAY LATER
    # ========================================================

    if (
        status == "confirmed"
        and payment_method == "pay_later"
    ):

        subject = (
            f"Pay Later Booking Confirmed — #{booking_id}"
        )


        html = f"""
<!DOCTYPE html>

<html>

<body style="
    margin:0;
    padding:0;
    background:#f4f8fb;
    font-family:Arial,Helvetica,sans-serif;
">

<div style="
    max-width:620px;
    margin:30px auto;
    padding:20px;
">

<div style="
    background:#ffffff;
    border-radius:18px;
    padding:35px;
    box-shadow:0 8px 30px rgba(0,0,0,.08);
">

<h2 style="
    color:#0077b6;
    text-align:center;
">

    🕒 Pay Later Booking

</h2>


<p>

    Booking
    <strong>#{booking_id}</strong>
    has been confirmed with Pay Later.

</p>


<div style="
    background:#f6fbfe;
    padding:20px;
    border-radius:12px;
    margin:20px 0;
">

<p>
<strong>Student:</strong>
{name}
</p>

<p>
<strong>Lesson:</strong>
{lesson_type}
</p>

<p>
<strong>Package:</strong>
{package}
</p>

<p>
<strong>Date:</strong>
{lesson_date}
</p>

<p>
<strong>Time:</strong>
{lesson_time}
</p>

<p>
<strong>Amount:</strong>
{price}
</p>

</div>


<p style="
    color:#0077b6;
    font-weight:bold;
">

Payment method: Pay Later

</p>


<p>

Customer will pay by the selected
Pay Later method.

</p>


</div>

</div>

</body>

</html>
"""


        return send_email(
            Config.OWNER_EMAIL,
            subject,
            html
        )


    # ========================================================
    # NOTHING TO SEND
    # ========================================================

    print(
        f"No owner email required for booking "
        f"#{booking_id}: "
        f"{status}/"
        f"{payment_status}/"
        f"{payment_method}"
    )

    return None


# ============================================================
# CUSTOMER — APPROVED
# ============================================================

def send_user_approved_email(booking):
    """
    Send customer an approval email.

    Includes:
        Pay Now
        Pay Later
    """

    booking = dict(booking)

    booking_id = booking["id"]

    name = booking.get(
        "name",
        booking.get("student_name", "Student")
    )

    customer_email = booking["email"]

    lesson_type = booking.get(
        "lesson_type",
        ""
    )

    package = booking.get(
        "package",
        ""
    )

    lesson_date = booking.get(
        "lesson_date",
        ""
    )

    lesson_time = booking.get(
        "lesson_time",
        ""
    )

    price = friendly_price(
        booking.get("price")
    )


    domain = str(
        Config.DOMAIN or ""
    ).strip().rstrip("/")


    pay_now_url = (
        f"{domain}"
        f"/pay-now/{booking_id}"
    )


    pay_later_url = (
        f"{domain}"
        f"/pay-later/{booking_id}"
    )


    subject = (
        "Your Swimming Lesson Has Been Approved! 🏊"
    )


    html = f"""
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

</head>


<body style="
    margin:0;
    padding:0;
    background:#eef7fb;
    font-family:Arial,Helvetica,sans-serif;
    color:#263238;
">


<div style="
    max-width:650px;
    margin:30px auto;
    padding:20px;
">


<div style="
    background:#ffffff;
    border-radius:20px;
    overflow:hidden;
    box-shadow:0 10px 35px rgba(0,0,0,.10);
">


<!-- HEADER -->

<div style="
    background:linear-gradient(
        135deg,
        #0077b6,
        #023e8a
    );
    padding:35px 25px;
    text-align:center;
    color:#ffffff;
">

<div style="
    font-size:45px;
">
🏊
</div>


<h1 style="
    margin:10px 0 0;
    font-size:26px;
">

    Lesson Approved!

</h1>


<p style="
    margin:8px 0 0;
">

    Millrod Swim Academy

</p>

</div>


<!-- CONTENT -->

<div style="
    padding:35px;
">


<h2 style="
    color:#023e8a;
    margin-top:0;
">

    Hi {name}! 👋

</h2>


<p style="
    line-height:1.6;
    font-size:16px;
">

Your swimming lesson request has been
approved.

We look forward to seeing you!

</p>


<!-- DETAILS -->

<div style="
    background:#f6fbfe;
    border-radius:14px;
    padding:22px;
    margin:25px 0;
">

<p>
<strong>Lesson:</strong>
{lesson_type}
</p>

<p>
<strong>Package:</strong>
{package}
</p>

<p>
<strong>Date:</strong>
{lesson_date}
</p>

<p>
<strong>Time:</strong>
{lesson_time}
</p>

<p style="
    margin-bottom:0;
">

<strong>Amount:</strong>
{price}

</p>

</div>


<h3 style="
    text-align:center;
    color:#023e8a;
">

Choose Your Payment Option

</h3>


<p style="
    text-align:center;
    color:#666666;
    line-height:1.5;
">

Pay securely online now, or choose
to pay later.

</p>


<!-- PAY NOW -->

<div style="
    text-align:center;
    margin:25px 0 12px;
">

<a
    href="{pay_now_url}"
    target="_blank"
    style="
        display:inline-block;
        background:#0077b6;
        color:#ffffff;
        padding:17px 34px;
        border-radius:10px;
        text-decoration:none;
        font-weight:bold;
        font-size:17px;
    "
>

💳 Pay Now

</a>

</div>


<!-- PAY LATER -->

<div style="
    text-align:center;
    margin:12px 0 25px;
">

<a
    href="{pay_later_url}"
    target="_blank"
    style="
        display:inline-block;
        background:#f4b400;
        color:#222222;
        padding:17px 34px;
        border-radius:10px;
        text-decoration:none;
        font-weight:bold;
        font-size:17px;
    "
>

🕒 Pay Later

</a>

</div>


<!-- BACKUP PAY NOW -->

<div style="
    background:#f8fafc;
    border:1px solid #dce5eb;
    border-radius:12px;
    padding:18px;
    margin-top:25px;
">

<p style="
    text-align:center;
    margin:0 0 10px;
    font-size:13px;
    color:#666666;
">

If the Pay Now button does not work:

</p>


<p style="
    margin:0;
    text-align:center;
    word-break:break-all;
    font-size:13px;
">

<a
    href="{pay_now_url}"
    target="_blank"
    style="
        color:#0077b6;
        text-decoration:underline;
    "
>

{pay_now_url}

</a>

</p>

</div>


<!-- BACKUP PAY LATER -->

<div style="
    background:#fffaf0;
    border:1px solid #f0dfb0;
    border-radius:12px;
    padding:18px;
    margin-top:15px;
">

<p style="
    text-align:center;
    margin:0 0 10px;
    font-size:13px;
    color:#666666;
">

If the Pay Later button does not work:

</p>


<p style="
    margin:0;
    text-align:center;
    word-break:break-all;
    font-size:13px;
">

<a
    href="{pay_later_url}"
    target="_blank"
    style="
        color:#b07b00;
        text-decoration:underline;
    "
>

{pay_later_url}

</a>

</p>

</div>


<p style="
    margin-top:30px;
    color:#777777;
    line-height:1.6;
    text-align:center;
">

Thank you for choosing
<strong>Millrod Swim Academy</strong>.

</p>


</div>


<!-- FOOTER -->

<div style="
    background:#f5f8fa;
    padding:20px;
    text-align:center;
    color:#777777;
    font-size:13px;
">

Millrod Swim Academy

</div>


</div>

</div>

</body>

</html>
"""


    return send_email(
        customer_email,
        subject,
        html
    )


# ============================================================
# CUSTOMER — REJECTED
# ============================================================

def send_user_rejected_email(booking):
    """
    Notify the customer that the booking request
    was not approved.
    """

    booking = dict(booking)

    customer_email = booking["email"]

    name = booking.get(
        "name",
        booking.get("student_name", "Customer")
    )

    lesson_date = booking.get(
        "lesson_date",
        ""
    )

    lesson_time = booking.get(
        "lesson_time",
        ""
    )

    subject = (
        "Update About Your Swimming Lesson Request"
    )


    html = f"""
<!DOCTYPE html>

<html>

<body style="
    margin:0;
    padding:0;
    background:#f4f8fb;
    font-family:Arial,Helvetica,sans-serif;
">

<div style="
    max-width:620px;
    margin:30px auto;
    padding:20px;
">

<div style="
    background:#ffffff;
    border-radius:18px;
    padding:35px;
    box-shadow:0 8px 30px rgba(0,0,0,.08);
">

<h2 style="
    text-align:center;
    color:#023e8a;
">

    Swimming Lesson Request Update

</h2>


<p>
Hi {name},
</p>


<p style="
    line-height:1.6;
">

Thank you for your interest in
Millrod Swim Academy.

Unfortunately, we are unable to approve
the swimming lesson request for:

</p>


<div style="
    background:#fff8f8;
    border-left:5px solid #dc3545;
    padding:18px;
    border-radius:8px;
    margin:25px 0;
">

<p>
<strong>Date:</strong>
{lesson_date}
</p>

<p>
<strong>Time:</strong>
{lesson_time}
</p>

</div>


<p style="
    line-height:1.6;
">

Please contact Millrod Swim Academy if
you would like to discuss another date
or time.

</p>


<p style="
    margin-top:30px;
">

Thank you,

<br>

<strong>
Millrod Swim Academy
</strong>

</p>


</div>

</div>

</body>

</html>
"""


    return send_email(
        customer_email,
        subject,
        html
    )


# ============================================================
# LESSON REMINDER
# ============================================================

def send_lesson_reminder(
    recipient,
    student_name,
    lesson_date,
    lesson_time,
    lesson_type=None,
    package=None,
):
    """
    Send a swimming lesson reminder email.
    """

    subject = (
        "🏊 Reminder: Your Swimming Lesson Is Tomorrow"
    )


    lesson_details = ""


    if lesson_type:

        lesson_details += f"""
        <p style="margin:7px 0;">
            <strong>Lesson:</strong>
            {lesson_type}
        </p>
        """


    if package:

        lesson_details += f"""
        <p style="margin:7px 0;">
            <strong>Package:</strong>
            {package}
        </p>
        """


    html = f"""
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

</head>


<body style="
    margin:0;
    padding:0;
    background:#f4f9fc;
    font-family:Arial,Helvetica,sans-serif;
    color:#333333;
">


<div style="
    max-width:620px;
    margin:30px auto;
    padding:20px;
">


<div style="
    background:#ffffff;
    border-radius:18px;
    overflow:hidden;
    box-shadow:0 8px 25px rgba(0,0,0,.08);
">


<div style="
    background:linear-gradient(
        135deg,
        #0077b6,
        #023e8a
    );
    padding:30px;
    text-align:center;
    color:#ffffff;
">

<div style="
    font-size:42px;
">

🏊

</div>


<h1 style="
    margin:0;
    font-size:25px;
">

Millrod Swim Academy

</h1>


<p style="
    margin:8px 0 0;
">

Swimming Lesson Reminder

</p>

</div>


<div style="
    padding:30px;
">


<h2 style="
    color:#023e8a;
    margin-top:0;
">

Hello {student_name}! 👋

</h2>


<p style="
    line-height:1.6;
">

This is a friendly reminder that your
swimming lesson is scheduled for tomorrow.

</p>


<div style="
    background:#f0f9ff;
    border-left:5px solid #0077b6;
    padding:18px;
    margin:22px 0;
    border-radius:8px;
">


<p style="margin:7px 0;">
<strong>📅 Date:</strong>
{lesson_date}
</p>


<p style="margin:7px 0;">
<strong>⏰ Time:</strong>
{lesson_time}
</p>


{lesson_details}


</div>


<p style="
    line-height:1.6;
">

Please arrive a few minutes early so we
can begin your lesson on time.

</p>


<p style="
    line-height:1.6;
">

If you need to make any changes to your
appointment, please contact Millrod Swim
Academy as soon as possible.

</p>


<p style="
    margin-top:30px;
">

We look forward to seeing you!

</p>


<p>

<strong>
Millrod Swim Academy
</strong>

</p>


</div>


<div style="
    background:#f5f8fa;
    padding:18px;
    text-align:center;
    color:#777777;
    font-size:13px;
">

Thank you for choosing
Millrod Swim Academy.

</div>


</div>

</div>

</body>

</html>
"""


    return send_email(
        recipient,
        subject,
        html
    )


# ============================================================
# CUSTOMER — BOOKING CONFIRMATION
# ============================================================

def send_booking_confirmation(booking):
    """
    Send the customer a booking confirmation email.

    This function is required by routes/payment.py.
    """

    booking = dict(booking)

    booking_id = booking.get("id")

    customer_email = booking.get("email")

    customer_name = booking.get(
        "name",
        booking.get(
            "student_name",
            "Customer"
        )
    )

    lesson_type = booking.get(
        "lesson_type",
        ""
    )

    package = booking.get(
        "package",
        ""
    )

    lesson_date = booking.get(
        "lesson_date",
        ""
    )

    lesson_time = booking.get(
        "lesson_time",
        ""
    )

    price = friendly_price(
        booking.get("price")
    )

    payment_status = booking.get(
        "payment_status",
        "pending"
    )

    payment_method = booking.get(
        "payment_method",
        "not_selected"
    )


    # ========================================================
    # PAYMENT MESSAGE
    # ========================================================

    if payment_status == "paid":

        payment_title = "Payment Confirmed ✓"

        payment_message = (
            "Your payment has been successfully received. "
            "Your swimming lesson is fully confirmed."
        )

        payment_color = "#198754"


    elif payment_method == "pay_later":

        payment_title = "Pay Later Selected"

        payment_message = (
            "Your lesson is confirmed. "
            "Payment will be collected when you arrive "
            "for your lesson."
        )

        payment_color = "#f4a261"


    else:

        payment_title = "Booking Confirmed"

        payment_message = (
            "Your swimming lesson has been confirmed."
        )

        payment_color = "#0077b6"


    subject = (
        "🏊 Your Millrod Swim Academy Booking Is Confirmed"
    )


    html = f"""
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

</head>


<body style="
    margin:0;
    padding:0;
    background:#eef7fb;
    font-family:Arial,Helvetica,sans-serif;
    color:#263238;
">


<div style="
    max-width:650px;
    margin:30px auto;
    padding:20px;
">


<div style="
    background:#ffffff;
    border-radius:20px;
    overflow:hidden;
    box-shadow:0 10px 35px rgba(0,0,0,.10);
">


<!-- =====================================================
     HEADER
====================================================== -->

<div style="
    background:linear-gradient(
        135deg,
        #0077b6,
        #023e8a
    );
    padding:35px 25px;
    text-align:center;
    color:#ffffff;
">

<div style="
    font-size:45px;
    margin-bottom:10px;
">

🏊

</div>


<h1 style="
    margin:0;
    font-size:27px;
">

Booking Confirmed!

</h1>


<p style="
    margin:9px 0 0;
    opacity:.92;
">

Millrod Swim Academy

</p>

</div>


<!-- =====================================================
     CONTENT
====================================================== -->

<div style="
    padding:35px;
">


<h2 style="
    color:#023e8a;
    margin-top:0;
">

Hi {customer_name}! 👋

</h2>


<p style="
    font-size:16px;
    line-height:1.6;
">

Your swimming lesson registration
is confirmed.

We look forward to seeing you!

</p>


<!-- =====================================================
     LESSON DETAILS
====================================================== -->

<div style="
    background:#f6fbfe;
    border:1px solid #dceef7;
    border-radius:14px;
    padding:22px;
    margin:25px 0;
">


<h3 style="
    margin-top:0;
    color:#023e8a;
">

Lesson Details

</h3>


<p>
<strong>Lesson:</strong>
{lesson_type}
</p>


<p>
<strong>Package:</strong>
{package}
</p>


<p>
<strong>Date:</strong>
{lesson_date}
</p>


<p>
<strong>Time:</strong>
{lesson_time}
</p>


<p style="
    margin-bottom:0;
">

<strong>Amount:</strong>
{price}

</p>


</div>


<!-- =====================================================
     PAYMENT STATUS
====================================================== -->

<div style="
    border-left:5px solid {payment_color};
    background:#fafafa;
    padding:18px 20px;
    margin-top:25px;
">


<strong style="
    color:{payment_color};
    font-size:17px;
">

{payment_title}

</strong>


<p style="
    margin:8px 0 0;
    line-height:1.5;
">

{payment_message}

</p>


</div>


<!-- =====================================================
     BOOKING ID
====================================================== -->

<p style="
    margin-top:25px;
    color:#777777;
    font-size:13px;
">

Booking ID:

<strong>
#{booking_id}
</strong>

</p>


<p style="
    margin-top:30px;
    line-height:1.6;
">

Thank you for choosing
<strong>Millrod Swim Academy</strong>.

We look forward to seeing you at your lesson!

</p>


</div>


<!-- =====================================================
     FOOTER
====================================================== -->

<div style="
    background:#f5f8fa;
    padding:20px;
    text-align:center;
    color:#777777;
    font-size:13px;
">

<strong>
Millrod Swim Academy
</strong>

<br>

Professional Swimming Lessons

</div>


</div>

</div>

</body>

</html>
"""


    return send_email(
        customer_email,
        subject,
        html
    )    
    
    
# ============================================================
# APPROVAL EMAIL COMPATIBILITY FUNCTION
# ============================================================

def send_booking_approved(booking):
    """
    Compatibility wrapper for the approval route.

    The application approval route may call
    send_booking_approved(), while the main customer
    approval email function is send_user_approved_email().
    """

    return send_user_approved_email(booking)  