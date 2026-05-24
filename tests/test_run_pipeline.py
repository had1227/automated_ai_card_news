import run_pipeline


def test_all_stages_export_html_without_render_or_review():
    assert run_pipeline.ALL_STAGES == ["collect", "rank", "facts", "export"]


def test_render_stage_remains_available_when_explicitly_selected():
    parser = run_pipeline.build_parser()
    args = parser.parse_args(["--render", "--export"])

    assert run_pipeline.selected_stages(args) == ["render", "export"]
