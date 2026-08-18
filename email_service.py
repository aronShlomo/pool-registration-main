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
    """Send one HTML email through Resend and return its response."""

    if not Config.RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY is not configured.")

    if not Config.EMAIL_FROM:
        raise RuntimeError("EMAIL_FROM is not configured.")

    if not to:
        raise RuntimeError("Recipient email is missing.")

    params = {
        "from": Config.EMAIL_FROM,
        "to": [str(to).strip()],
        "subject": subject,
        "html": html
    }

    print("========================================")
    print("RESEND EMAIL SEND")
    print("FROM:", Config.EMAIL_FROM)
    print("TO:", str(to).strip())
    print("SUBJECT:", subject)
    print("========================================")

    response = resend.Emails.send(params)

    print("RESEND RESPONSE:", repr(response))

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

    if price.startswith("$"):
        return price

    return f"${price}"


# ============================================================
# OWNER — NEW REGISTRATION REQUEST
# ============================================================

def send_admin_notification(booking):
    """
    Notify the owner about a booking.

    Behavior depends on the booking/payment status.

    Pending:
        Owner receives Approve / Reject buttons.

    Confirmed + paid:
        Owner receives payment notification.

    Confirmed + Pay Later:
        Owner receives Pay Later notification.
    """

    booking = dict(booking)

    booking_id = booking["id"]

    name = booking["name"]
    email = booking["email"]
    phone = booking["phone"]

    lesson_type = booking["lesson_type"]
    package = booking["package"]

    lesson_date = booking["lesson_date"]
    lesson_time = booking["lesson_time"]

    price = friendly_price(
        booking["price"]
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

    approval_token = booking.get(
        "approval_token"
    )


    # ========================================================
    # NEW REQUEST — WAITING FOR OWNER
    # ========================================================

    if status == "pending":

        if not approval_token:
            raise RuntimeError(
                "Approval token is missing from booking."
            )

        approve_url = (
            f"{Config.DOMAIN}"
            f"/api/approve-booking"
            f"?token={approval_token}"
        )

        reject_url = (
            f"{Config.DOMAIN}"
            f"/api/reject-booking"
            f"?token={approval_token}"
        )

        subject = (
            f"New Lesson Request — {name}"
        )

        html = f"""
        <!DOCTYPE html>
        <html>
        <body style="
            margin:0;
            padding:0;
            background:#f4f8fb;
            font-family:Arial,Helvetica,sans-serif;
            color:#263238;
        ">

        <div style="
            max-width:650px;
            margin:0 auto;
            padding:35px 20px;
        ">

            <div style="
                background:#ffffff;
                border-radius:18px;
                overflow:hidden;
                box-shadow:0 8px 30px rgba(0,0,0,0.08);
            ">

                <div style="
                    background:#0077b6;
                    padding:30px;
                    text-align:center;
                    color:#ffffff;
                ">

                    <div style="
                        font-size:36px;
                        margin-bottom:8px;
                    ">
                        🏊
                    </div>

                    <h1 style="
                        margin:0;
                        font-size:25px;
                    ">
                        New Lesson Request
                    </h1>

                    <p style="
                        margin:8px 0 0;
                        opacity:0.9;
                    ">
                        Millrod Swim Academy
                    </p>

                </div>


                <div style="padding:35px;">

                    <p style="
                        font-size:16px;
                        line-height:1.6;
                        margin-top:0;
                    ">
                        A new swimming lesson registration
                        is waiting for your review.
                    </p>


                    <div style="
                        background:#f7fbfd;
                        border-radius:12px;
                        padding:22px;
                        margin:25px 0;
                    ">

                        <p>
                            <strong>Student:</strong>
                            {name}
                        </p>

                        <p>
                            <strong>Email:</strong>
                            {email}
                        </p>

                        <p>
                            <strong>Phone:</strong>
                            {phone}
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

                        <p style="margin-bottom:0;">
                            <strong>Price:</strong>
                            {price}
                        </p>

                    </div>


                    <p style="
                        text-align:center;
                        font-weight:bold;
                        margin-bottom:22px;
                    ">
                        Would you like to approve this request?
                    </p>


                    <div style="
                        text-align:center;
                        margin:25px 0;
                    ">

                        <a
                            href="{approve_url}"
                            style="
                                display:inline-block;
                                background:#198754;
                                color:#ffffff;
                                padding:14px 28px;
                                border-radius:9px;
                                text-decoration:none;
                                font-weight:bold;
                                margin:5px;
                            "
                        >
                            ✔ Approve Booking
                        </a>

                        <a
                            href="{reject_url}"
                            style="
                                display:inline-block;
                                background:#dc3545;
                                color:#ffffff;
                                padding:14px 28px;
                                border-radius:9px;
                                text-decoration:none;
                                font-weight:bold;
                                margin:5px;
                            "
                        >
                            ✖ Reject Booking
                        </a>

                    </div>


                    <p style="
                        color:#7a7a7a;
                        font-size:13px;
                        line-height:1.5;
                        text-align:center;
                        margin-top:30px;
                    ">
                        Approving the request will automatically
                        send the customer an email with Pay Now
                        and Pay Later options.
                    </p>

                </div>

            </div>

        </div>

        </body>
        </html>
        """

        print("========================================")
        print("OWNER APPROVAL EMAIL")
        print("BOOKING ID:", booking_id)
        print("OWNER EMAIL:", Config.OWNER_EMAIL)
        print("APPROVAL TOKEN PRESENT:", bool(approval_token))
        print("APPROVE URL:", approve_url)
        print("========================================")

        return send_email(
            Config.OWNER_EMAIL,
            subject,
            html
        )


    # ========================================================
    # STRIPE PAYMENT RECEIVED
    # ========================================================

    if (
        status == "confirmed"
        and payment_status == "paid"
    ):

        subject = (
            f"Payment Received — {name}"
        )

        html = f"""
        <div style="
            font-family:Arial,Helvetica,sans-serif;
            max-width:650px;
            margin:auto;
            padding:30px;
        ">

            <div style="
                background:#ffffff;
                border-radius:16px;
                padding:35px;
                box-shadow:0 8px 30px rgba(0,0,0,.08);
            ">

                <div style="
                    text-align:center;
                    font-size:45px;
                ">
                    💳
                </div>

                <h2 style="
                    color:#198754;
                    text-align:center;
                ">
                    Payment Received
                </h2>

                <p style="text-align:center;">
                    Booking #{booking_id} has been paid
                    successfully.
                </p>

                <hr style="
                    border:0;
                    border-top:1px solid #eeeeee;
                    margin:25px 0;
                ">

                <p><strong>Student:</strong> {name}</p>

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

                <p>
                    <strong>Payment:</strong>
                    Paid by card
                </p>

            </div>

        </div>
        """

        return send_email(
            Config.OWNER_EMAIL,
            subject,
            html
        )


    # ========================================================
    # PAY LATER SELECTED
    # ========================================================

    if (
        status == "confirmed"
        and payment_status == "pending"
        and payment_method == "cash_or_zelle"
    ):

        subject = (
            f"Pay Later Selected — {name}"
        )

        html = f"""
        <div style="
            font-family:Arial,Helvetica,sans-serif;
            max-width:650px;
            margin:auto;
            padding:30px;
        ">

            <div style="
                background:#ffffff;
                border-radius:16px;
                padding:35px;
                box-shadow:0 8px 30px rgba(0,0,0,.08);
            ">

                <div style="
                    font-size:45px;
                    text-align:center;
                ">
                    🕒
                </div>

                <h2 style="
                    color:#0077b6;
                    text-align:center;
                ">
                    Pay Later Selected
                </h2>

                <p style="text-align:center;">
                    The customer chose to pay by
                    Cash or Zelle when they arrive.
                </p>

                <hr style="
                    border:0;
                    border-top:1px solid #eeeeee;
                    margin:25px 0;
                ">

                <p><strong>Student:</strong> {name}</p>

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
                    <strong>Amount Due:</strong>
                    {price}
                </p>

            </div>

        </div>
        """

        return send_email(
            Config.OWNER_EMAIL,
            subject,
            html
        )


    print(
        f"No owner email required for booking "
        f"#{booking_id}: "
        f"{status}/{payment_status}/{payment_method}"
    )

    return None


# ============================================================
# CUSTOMER — APPROVED
# ============================================================

def send_user_approved_email(booking):
    """
    Customer receives this email after owner approval.

    Customer can choose:
        Pay Now
        Pay Later
    """

    booking = dict(booking)

    booking_id = booking["id"]

    name = booking["name"]

    lesson_type = booking["lesson_type"]

    package = booking["package"]

    lesson_date = booking["lesson_date"]

    lesson_time = booking["lesson_time"]

    price = friendly_price(
        booking["price"]
    )


    pay_now_url = (
        f"{Config.DOMAIN}"
        f"/api/pay-now/{booking_id}"
    )

    pay_later_url = (
        f"{Config.DOMAIN}"
        f"/api/pay-later/{booking_id}"
    )


    subject = (
        "Your Swimming Lesson Has Been Approved! 🏊"
    )


    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="
        margin:0;
        padding:0;
        background:#f4f8fb;
        font-family:Arial,Helvetica,sans-serif;
        color:#263238;
    ">

    <div style="
        max-width:650px;
        margin:0 auto;
        padding:35px 20px;
    ">

        <div style="
            background:#ffffff;
            border-radius:18px;
            overflow:hidden;
            box-shadow:0 8px 30px rgba(0,0,0,.08);
        ">

            <div style="
                background:#0077b6;
                color:#ffffff;
                text-align:center;
                padding:35px 25px;
            ">

                <div style="font-size:45px;">
                    ✓
                </div>

                <h1 style="
                    margin:10px 0 5px;
                    font-size:26px;
                ">
                    Great News, {name}!
                </h1>

                <p style="margin:0;">
                    Your lesson request has been approved.
                </p>

            </div>


            <div style="padding:35px;">

                <p style="
                    font-size:16px;
                    line-height:1.6;
                ">
                    We're happy to welcome you to
                    <strong>Millrod Swim Academy</strong>.
                    Your requested lesson has been approved.
                </p>


                <div style="
                    background:#f7fbfd;
                    padding:22px;
                    border-radius:12px;
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

                    <p style="margin-bottom:0;">
                        <strong>Amount Due:</strong>
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
                    to pay with Cash or Zelle when you arrive.
                </p>


                <div style="
                    text-align:center;
                    margin:30px 0 15px;
                ">

                    <a
                        href="{pay_now_url}"
                        style="
                            display:inline-block;
                            background:#0077b6;
                            color:#ffffff;
                            padding:15px 30px;
                            border-radius:9px;
                            text-decoration:none;
                            font-weight:bold;
                            margin:6px;
                        "
                    >
                        💳 Pay Now
                    </a>

                    <a
                        href="{pay_later_url}"
                        style="
                            display:inline-block;
                            background:#f4b400;
                            color:#222222;
                            padding:15px 30px;
                            border-radius:9px;
                            text-decoration:none;
                            font-weight:bold;
                            margin:6px;
                        "
                    >
                        🕒 Pay Later
                    </a>

                </div>


                <p style="
                    color:#777777;
                    font-size:13px;
                    text-align:center;
                    margin-top:30px;
                    line-height:1.5;
                ">
                    Pay Later means you may pay by Cash
                    or Zelle when you arrive for your lesson.
                </p>

            </div>

        </div>

    </div>

    </body>
    </html>
    """


    return send_email(
        booking["email"],
        subject,
        html
    )


# ============================================================
# CUSTOMER — REJECTED
# ============================================================

def send_user_rejected_email(booking):
    """
    Friendly customer notification when a request cannot
    be approved.
    """

    booking = dict(booking)

    name = booking["name"]

    lesson_date = booking["lesson_date"]

    lesson_time = booking["lesson_time"]


    subject = (
        "Update About Your Swimming Lesson Request"
    )


    html = f"""
    <div style="
        background:#f4f8fb;
        padding:35px 20px;
        font-family:Arial,Helvetica,sans-serif;
    ">

        <div style="
            max-width:620px;
            margin:auto;
            background:#ffffff;
            border-radius:16px;
            padding:35px;
            box-shadow:0 8px 30px rgba(0,0,0,.08);
        ">

            <h2 style="
                color:#023e8a;
                text-align:center;
            ">
                Lesson Request Update
            </h2>

            <p>
                Hi {name},
            </p>

            <p style="line-height:1.6;">
                Thank you for your interest in
                Millrod Swim Academy.
            </p>

            <p style="line-height:1.6;">
                Unfortunately, we're unable to approve
                your requested lesson time:
            </p>

            <div style="
                background:#f7fbfd;
                border-radius:10px;
                padding:18px;
                margin:20px 0;
            ">

                <p>
                    <strong>Date:</strong>
                    {lesson_date}
                </p>

                <p style="margin-bottom:0;">
                    <strong>Time:</strong>
                    {lesson_time}
                </p>

            </div>

            <p style="line-height:1.6;">
                Please visit our website and choose another
                available date or time. We'd be happy to
                work with you to find an option that works.
            </p>

            <p style="
                margin-top:30px;
                color:#555555;
            ">
                Millrod Swim Academy 🏊
            </p>

        </div>

    </div>
    """


    return send_email(
        booking["email"],
        subject,
        html
    )


# ============================================================
# CUSTOMER — FINAL CONFIRMATION
# ============================================================

def send_booking_confirmation(
    customer_email,
    customer_name,
    lesson_type,
    package,
    lesson_date,
    lesson_time,
    payment_status,
    price
):
    """
    Final confirmation.

    Called after:
        Stripe payment
        OR
        Pay Later selection
    """

    price = friendly_price(
        price
    )


    # ========================================================
    # PAID WITH STRIPE
    # ========================================================

    if payment_status == "paid":

        payment_title = (
            "Payment Received ✓"
        )

        payment_message = (
            "Your online payment has been received "
            "successfully. No payment is due when you arrive."
        )

        payment_color = "#198754"

        subject = (
            "Payment Received — Lesson Confirmed 🏊"
        )


    # ========================================================
    # PAY LATER
    # ========================================================

    else:

        payment_title = (
            "Pay Later Confirmed"
        )

        payment_message = (
            "Your lesson is confirmed. "
            "You may pay by Cash or Zelle when you arrive."
        )

        payment_color = "#f4a100"

        subject = (
            "Swimming Lesson Confirmed 🏊"
        )


    html = f"""
    <!DOCTYPE html>
    <html>

    <body style="
        margin:0;
        background:#f4f8fb;
        padding:35px 20px;
        font-family:Arial,Helvetica,sans-serif;
        color:#263238;
    ">

        <div style="
            max-width:650px;
            margin:auto;
            background:#ffffff;
            border-radius:18px;
            overflow:hidden;
            box-shadow:0 8px 30px rgba(0,0,0,.08);
        ">

            <div style="
                background:#0077b6;
                color:#ffffff;
                text-align:center;
                padding:35px;
            ">

                <div style="font-size:45px;">
                    🏊
                </div>

                <h1 style="
                    margin:10px 0 0;
                    font-size:26px;
                ">
                    Lesson Confirmed
                </h1>

            </div>


            <div style="padding:35px;">

                <p style="font-size:17px;">
                    Hi {customer_name},
                </p>

                <p style="
                    line-height:1.6;
                    color:#555555;
                ">
                    Your swimming lesson registration
                    is confirmed. We look forward to
                    seeing you!
                </p>


                <div style="
                    background:#f7fbfd;
                    padding:22px;
                    border-radius:12px;
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

                    <p style="margin-bottom:0;">
                        <strong>Amount:</strong>
                        {price}
                    </p>

                </div>


                <div style="
                    border-left:5px solid {payment_color};
                    background:#fafafa;
                    padding:18px 20px;
                    margin-top:25px;
                ">

                    <strong style="
                        color:{payment_color};
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


                <p style="
                    margin-top:35px;
                    line-height:1.6;
                    color:#555555;
                ">
                    Thank you for choosing
                    <strong>Millrod Swim Academy</strong>.
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
    
def send_lesson_reminder(
    recipient,
    student_name,
    lesson_date,
    lesson_time,
    lesson_type=None,
    package=None,
):
    """
    Send a swimming lesson reminder email to the customer.
    """

    try:
        import resend

        subject = "🏊 Reminder: Your Swimming Lesson Is Tomorrow"

        lesson_details = ""

        if lesson_type:
            lesson_details += f"""
                <p>
                    <strong>Lesson:</strong>
                    {lesson_type}
                </p>
            """

        if package:
            lesson_details += f"""
                <p>
                    <strong>Package:</strong>
                    {package}
                </p>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport"
                  content="width=device-width, initial-scale=1.0">
        </head>

        <body style="
            margin:0;
            padding:0;
            background:#f4f9fc;
            font-family:Arial,Helvetica,sans-serif;
            color:#333;
        ">

            <div style="
                max-width:600px;
                margin:30px auto;
                background:#ffffff;
                border-radius:16px;
                overflow:hidden;
                box-shadow:0 8px 25px rgba(0,0,0,0.08);
            ">

                <div style="
                    background:linear-gradient(
                        135deg,
                        #0077b6,
                        #023e8a
                    );
                    padding:30px;
                    text-align:center;
                    color:white;
                ">

                    <div style="
                        font-size:42px;
                        margin-bottom:10px;
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
                        opacity:0.9;
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

                    <p>
                        This is a friendly reminder that
                        your swimming lesson is scheduled
                        for tomorrow.
                    </p>


                    <div style="
                        background:#f0f9ff;
                        border-left:5px solid #0077b6;
                        padding:18px;
                        margin:22px 0;
                        border-radius:8px;
                    ">

                        <p style="margin:5px 0;">
                            <strong>📅 Date:</strong>
                            {lesson_date}
                        </p>

                        <p style="margin:5px 0;">
                            <strong>⏰ Time:</strong>
                            {lesson_time}
                        </p>

                        {lesson_details}

                    </div>


                    <p>
                        Please arrive a few minutes early
                        so we can begin your lesson on time.
                    </p>


                    <p>
                        If you need to make any changes
                        to your appointment, please contact
                        Millrod Swim Academy as soon as possible.
                    </p>


                    <p style="
                        margin-top:30px;
                    ">
                        We look forward to seeing you! 🏊‍♂️
                    </p>


                    <p>
                        <strong>
                            Millrod Swim Academy
                        </strong>
                    </p>

                </div>


                <div style="
                    background:#f4f7fb;
                    padding:18px;
                    text-align:center;
                    color:#7a8793;
                    font-size:12px;
                ">

                    This is an automated reminder
                    from Millrod Swim Academy.

                </div>

            </div>

        </body>
        </html>
        """

        response = resend.Emails.send({
            "from": Config.EMAIL_FROM,
            "to": [recipient],
            "subject": subject,
            "html": html,
        })

        print(
            f"Lesson reminder sent successfully to {recipient}"
        )

        return response

    except Exception as e:

        print(
            f"Error sending lesson reminder: {e}"
        )

        return None    