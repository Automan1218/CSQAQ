from csqaq.rules import load_inventory_rules


class TestRuleLoader:
    def test_load_rules(self):
        rules = load_inventory_rules()
        assert isinstance(rules, list)
        assert len(rules) >= 4  # initial rule set has 4 rules
        assert all("name" in r and "description" in r for r in rules)

    def test_rules_have_required_fields(self):
        rules = load_inventory_rules()
        for rule in rules:
            assert isinstance(rule["name"], str)
            assert isinstance(rule["description"], str)
            assert len(rule["description"]) > 10  # meaningful descriptions

    def test_rules_format_as_prompt(self):
        """Rules should be formattable into a prompt string."""
        rules = load_inventory_rules()
        prompt_text = "\n".join(f"- {r['name']}: {r['description']}" for r in rules)
        assert "吸货" in prompt_text
        assert "控盘" in prompt_text
