"""Verified Egyptian Arabic phrase bank and spoken response templates."""

from typing import Dict, Any
from src.domain.schemas import Plan, RecommendationResponse


class EgyptianPhraseBank:
    """Templates for generating colloquial Egyptian Arabic spoken explanations."""

    GREETINGS = [
        "أهلاً بيك يا حاج، نورت نبتة.",
        "مرحباً بيك يا حاج، إحنا معاك خطوة بخطوة عشان أرضك ومحصولك.",
    ]

    DISCLAIMER = "ده تقدير استرشادي مش ضمان، والأسعار والمحصول بيتغيروا حسب السوق ورعاية الأرض."

    ENGINEER_CONTACT = "لو تحب، تقدر تتواصل مع الباشمهندس الزراعي في الإدارة الزراعية أو الجمعية لمتابعة أرضك."

    @staticmethod
    def format_confirmation_request(
        location_ar: str,
        area_str: str,
        water_source_ar: str,
        previous_crop_ar: str,
    ) -> str:
        """Formulate natural confirmation dialogue phrase before submitting to decision engine."""
        return (
            f"تمام يا حاج، فهمت إن أرضك في {location_ar}، ومساحتها {area_str}، "
            f"والمية بتجيلك من {water_source_ar}، والموسم اللي فات كنت زارع {previous_crop_ar}. "
            "صح كده يا حاج؟"
        )

    @staticmethod
    def format_plan_spoken_response(plan: Plan) -> str:
        """Generate verified colloquial speech for a single recommendation plan."""
        m = plan.metrics
        crop_ar = plan.primary_crop_ar
        archetype = plan.archetype
        profit_feddan = int(m.net_profit_egp_per_feddan)
        water_feddan = int(m.water_demand_m3_per_feddan)

        if archetype == "الأكسب":
            intro = f"الاختيار الأول: الأكسب، هو زراعة {crop_ar}."
            benefit = f"ده بيحقق أعلى صافي ربح حوالي {profit_feddan:,} جنيه للفدان."
        elif archetype == "الأوفر في المية":
            intro = f"الاختيار التاني: الأوفر في المية، هو زراعة {crop_ar}."
            benefit = f"ده بيستهلك حوالي {water_feddan:,} متر مكعب مية للفدان، ويوفر معاك في السولار."
        else:  # الأأمن
            intro = f"الاختيار التالت: الأأمن، هو زراعة {crop_ar}."
            benefit = f"ده محصول استراتيجي ومضمون في التسويق وبيعمل حوالي {profit_feddan:,} جنيه للفدان."

        advice = plan.key_advice_ar

        return f"{intro} {benefit} نصيحتنا ليك: {advice} (وده تقدير استرشادي مش ضمان)."

    @classmethod
    def format_full_recommendation_audio_script(cls, response: RecommendationResponse) -> str:
        """Generate complete audio narration presenting the 3 options clearly."""
        lines = [
            f"يا حاج، بناءً على بيانات المناخ وتربة أرضك في {response.farm_location}، حسبنا لك ٣ اختيارات مدروسة:"
        ]
        for p in response.recommendations:
            lines.append(cls.format_plan_spoken_response(p))

        lines.append(cls.DISCLAIMER)
        return " ".join(lines)
