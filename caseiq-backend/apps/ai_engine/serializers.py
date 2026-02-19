from rest_framework import serializers


class AnalyzeScenarioInputSerializer(serializers.Serializer):
    """
    Input serializer for AI analysis endpoint.
    """
    text = serializers.CharField(
        min_length=20,
        max_length=5000,
        help_text="Describe your legal scenario in detail."
    )
    language = serializers.ChoiceField(
        choices=["en", "hi"],
        default="en",
        help_text="Language for AI response (English or Hindi)"
    )


class AnalyzeScenarioOutputSerializer(serializers.Serializer):
    """
    Output serializer for AI analysis response.
    """
    query_id = serializers.IntegerField()
    status = serializers.CharField()
    message = serializers.CharField()