"""Small synthetic theme; never writes to a customer project."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import codemap
import verify_theme


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.write('style.css', '/* Theme Name: Fixture */')
        self.write('UI/About.html', '<section class="about-1"></section>')
        self.write('templates/template-about.php', "<?php get_template_part('template-parts/about/history'); get_template_part('template-parts/shared/cta');")
        self.write('templates/template-home.php', "<?php get_template_part('template-parts/shared/cta');")
        self.write('template-parts/shared/cta.php', '<section class="cta"></section>')
        self.write('template-parts/about/history.php', '''<?php
while (have_rows('about_history_list')): the_row(); get_sub_field('image'); endwhile;
get_sub_field('image');
get_template_part($part);
$unused = ['post_type' => 'fake'];
new WP_Query(['post_type' => 'post']);
// get_template_part('template-parts/shared/cta');
$s = "get_field('fake')";
?>
<section class="about-1"></section>''')
        fields = [{'key': 'field_' + name, 'name': name, 'type': 'repeater', 'sub_fields': [
            {'key': 'field_' + name + '_image', 'name': 'image', 'type': 'image', 'return_format': 'id'}
        ]} for name in ('about_history_list', 'about_goal_list')]
        self.write('acf-json/group_about.json', json.dumps({'key': 'group_about', 'title': 'About', 'fields': fields,
            'location': [[{'param': 'page_template', 'operator': '==', 'value': 'templates/template-about.php'}]]}))

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')

    def graph(self):
        return codemap.build_graph(self.root)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPTS / 'codemap.py'), *args, '--root', str(self.root)], capture_output=True, text=True, encoding='utf-8')

    def test_duplicate_subfields(self):
        edges = self.graph()['edges']
        targets = {e['target'] for e in edges if e['type'] == 'uses_field' and e['confidence'] == 'static'}
        self.assertIn('ACFField:field_about_history_list_image', targets)
        self.assertNotIn('ACFField:field_about_goal_list_image', targets)
        self.assertTrue(any(e['type'] == 'uses_field' and e['confidence'] == 'unresolved' for e in edges))

    def test_integrity(self):
        graph = self.graph()
        ids = {n['id'] for n in graph['nodes']}
        self.assertTrue(all(e['source'] in ids and e['target'] in ids for e in graph['edges']))

    def test_query_scope(self):
        edges = self.graph()['edges']
        self.assertFalse(any(e['target'] == 'CPT:fake' for e in edges))

    def test_comments_and_strings(self):
        edges = self.graph()['edges']
        self.assertFalse(any(e['source'].endswith('history.php') and e['target'].endswith('cta.php') for e in edges))
        self.assertFalse(any(e['target'] == 'ACFFieldName:fake' for e in edges))

    def test_section_comment_regression(self):
        self.write('UI/Home.html', '<section class="home-2"></section>')
        self.write('home.php', '<?php // home-2\n $unused = \'<section class="home-2">\';')
        with contextlib.redirect_stdout(io.StringIO()) as out:
            result = verify_theme.check_parity(self.root, 'UI/Home.html', ['home.php'])
        self.assertNotEqual(result, 0, out.getvalue())

    def test_query_page(self):
        self.assertEqual(self.cli('build').returncode, 0)
        result = self.cli('query', '--page', 'about', '--format', 'json')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('templates/template-about.php', result.stdout)

    def test_unsupported_arguments_fail(self):
        self.assertNotEqual(self.cli('query', 'anything').returncode, 0)

    def result(self, command='query', *args):
        self.assertEqual(self.cli('build').returncode, 0)
        result = self.cli(command, *args, '--format', 'json')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_query_component(self):
        result = self.result('query', '--file', 'template-parts/about/history.php')
        self.assertIn('templates/template-about.php', result['related_files'])
        self.assertIn('acf-json/group_about.json', result['related_files'])
        self.assertNotIn('templates/template-home.php', result['related_files'])

    def test_field_path_and_group(self):
        result = self.result('query', '--field', 'about_history_list.image')
        self.assertFalse(result['ambiguous_target'])
        self.assertEqual(result['items'][0]['node']['key'], 'field_about_history_list_image')
        result = self.result('query', '--field', 'image')
        self.assertTrue(result['ambiguous_target'])
        self.assertEqual(self.result('query', '--group', 'group_about')['status'], 'ok')

    def test_shared_impact(self):
        result = self.result('impact', '--file', 'template-parts/shared/cta.php')
        consumers = {i['node']['id'] for i in result['items'] if i['category'] == 'direct_consumer'}
        self.assertEqual(consumers, {'templates/template-about.php', 'templates/template-home.php'})
        self.assertIn('template-parts/shared/cta.php', result['shared_components'])
        self.assertTrue(result['recommended_checks'])

    def test_acf_json_impact(self):
        result = self.result('impact', '--file', 'acf-json/group_about.json')
        self.assertTrue(any(i['category'] == 'direct_consumer' and i['node']['id'].endswith('history.php') for i in result['items']))

    def test_dynamic_not_confirmed(self):
        edges = [e for e in self.graph()['edges'] if e['type'] == 'includes' and e['source'].endswith('history.php')]
        self.assertTrue(edges)
        self.assertTrue(all(e['confidence'] == 'dynamic' for e in edges))

    def test_stale_is_read_only(self):
        self.cli('build')
        before = (self.root / '.ai-map/graph.json').read_bytes()
        self.write('new.php', '<?php get_field("x");')
        result = self.cli('query', '--page', 'about', '--format', 'json')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)['items'], [])
        self.assertEqual(before, (self.root / '.ai-map/graph.json').read_bytes())

    def test_missing_target(self):
        self.cli('build')
        result = self.cli('query', '--file', 'missing.php', '--format', 'json')
        self.assertEqual(result.returncode, 3)
        self.assertEqual(json.loads(result.stdout)['status'], 'missing_target')

    def test_bounded_json(self):
        full = self.result('query', '--page', 'about')
        result = self.result('query', '--page', 'about', '--max-items', '1')
        self.assertEqual(len(result['items']), 1)
        self.assertTrue(result['truncated'])
        self.assertEqual(result['omitted_count'], full['total_items'] - 1)
        self.assertEqual(result['items'][0]['category'], 'exact_target')

    def test_real_markup_static_only(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            result = verify_theme.check_parity(self.root, 'UI/About.html', ['templates/template-about.php'])
        self.assertEqual(result, 0, out.getvalue())
        self.assertIn('[NOT RUN]', out.getvalue())
        self.assertIn('static markers only', out.getvalue())

    def test_installer_preserves_state(self):
        saved = {'PROJECT_OVERRIDES.md': 'Kit version: `1.0.0`\nApproved decisions',
                 'HANDOVER_TRACKING.md': 'Kit version: `1.0.0`\nIn progress',
                 'PROJECT_VARIANTS.md': 'My variants', 'handoffs/about.md': 'Kit version: `1.0.0`\nApproved mapping'}
        for path, value in saved.items():
            self.write(path, value)
        for extra in (['--dry-run'], []):
            result = subprocess.run([sys.executable, str(SCRIPTS / 'install_kit.py'), '--target', str(self.root), '--upgrade', *extra], capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for path, value in saved.items():
                self.assertEqual((self.root / path).read_text(encoding='utf-8'), value)

    def test_installer_reports_build_failure(self):
        self.write('acf-json/bad.json', '{invalid')
        result = subprocess.run([sys.executable, str(SCRIPTS / 'install_kit.py'), '--target', str(self.root)], capture_output=True, text=True, encoding='utf-8')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('HOÀN TẤT! Bước tiếp theo', result.stdout)
        self.assertIn('[FAIL]', result.stdout)

    def test_markdown_not_cut(self):
        graph = self.graph()
        graph['nodes'].extend({'id': f'page-{i}.php', 'type': 'Template'} for i in range(180))
        markdown, shards = codemap.render_markdown_outputs(graph)
        self.assertIn('page-179.php', markdown)
        self.assertTrue(all('|' not in part.splitlines()[4] for part in shards.values()))

    def test_nested_rows_and_field_keys(self):
        data = json.loads((self.root / 'acf-json/group_about.json').read_text())
        data['fields'][0]['sub_fields'].append({'key': 'field_children', 'name': 'children', 'type': 'repeater',
            'sub_fields': [{'key': 'field_nested_image', 'name': 'image', 'type': 'image'}]})
        self.write('acf-json/group_about.json', json.dumps(data))
        self.write('nested.php', "<?php while(have_rows('about_history_list')) { the_row(); while(have_rows('children')) { the_row(); get_sub_field('image'); } get_sub_field('image'); } get_sub_field('field_nested_image');")
        edges = [e for e in self.graph()['edges'] if e['source'] == 'nested.php' and e['confidence'] == 'static']
        targets = {e['target'] for e in edges}
        self.assertIn('ACFField:field_nested_image', targets)
        self.assertIn('ACFField:field_about_history_list_image', targets)
        self.assertNotIn('ACFField:field_about_goal_list_image', targets)

    def test_dynamic_and_literal_template_variants(self):
        self.write('parts.php', "<?php get_template_part('template-parts/shared/cta', $name); get_template_part('template-parts/shared/cta', 'small'); get_template_part('template-parts/shared/' . 'cta');")
        self.write('template-parts/shared/cta-small.php', '<p>Small</p>')
        edges = [e for e in self.graph()['edges'] if e['source'] == 'parts.php']
        self.assertEqual(sum(e['confidence'] == 'dynamic' for e in edges), 2)
        self.assertTrue(any(e['target'].endswith('cta-small.php') and e['confidence'] == 'static' for e in edges))

    def test_include_and_helpers(self):
        self.write('inc/helper.php', '<?php function helper() {}')
        self.write('functions.php', "<?php require_once __DIR__ . '/inc/helper.php'; helper();")
        self.write('inc/caller.php', '<?php helper();')
        result = self.result('impact', '--file', 'inc/helper.php')
        consumers = {i['node']['id'] for i in result['items'] if i['category'] == 'direct_consumer'}
        self.assertEqual(consumers, {'functions.php', 'inc/caller.php'})

    def test_nested_and_variable_queries_unresolved(self):
        self.write('queries.php', "<?php new WP_Query(['meta_query' => [['post_type' => 'fake']]]); get_posts($args); $x = ['post_type' => 'also_fake'];")
        edges = [e for e in self.graph()['edges'] if e['source'] == 'queries.php' and e['type'] == 'queries']
        self.assertEqual(len(edges), 2)
        self.assertTrue(all(e['confidence'] == 'unresolved' for e in edges))

    def test_comment_markup_heredoc_and_dynamic_class(self):
        from kitlib import section_classes, php_calls
        source = '''<?php
$x = <<<'TXT'
get_field('fake'); <section class="home-2">
TXT;
?>
<!-- <section class="home-2"> -->
<script>const s = '<section class="home-2">';</script>
<section class="<?php echo $class; ?> home-2"></section>
'''
        self.assertEqual(section_classes(source, php=True), [])
        self.assertFalse(any(c['name'] == 'get_field' for c in php_calls(source)))

    def test_graph_render_comment_not_confirmed(self):
        self.write('fake.php', '<?php /* <section class="about-1"> */ $s = \'<section class="about-1">\';')
        self.assertFalse(any(e['type'] == 'renders' and e['source'] == 'fake.php' for e in self.graph()['edges']))

    def test_old_schema_and_corrupt_map(self):
        self.cli('build')
        self.write('.ai-map/graph.json', '{bad')
        result = self.cli('query', '--page', 'about', '--format', 'json')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['items'], [])
        self.cli('build')
        meta = json.loads((self.root / '.ai-map/meta.json').read_text())
        meta.pop('schema_version')
        self.write('.ai-map/meta.json', json.dumps(meta))
        self.assertEqual(self.cli('check').returncode, 1)

    def test_added_modified_deleted_freshness(self):
        for operation in ('add', 'modify', 'delete'):
            self.cli('build')
            if operation == 'add':
                self.write('extra.php', '<?php')
            elif operation == 'modify':
                self.write('extra.php', '<?php // changed')
            else:
                (self.root / 'extra.php').unlink()
            self.assertEqual(self.cli('check').returncode, 1, operation)

    def test_cli_root_before_subcommand_and_invalid_limits(self):
        self.cli('build')
        result = subprocess.run([sys.executable, str(SCRIPTS / 'codemap.py'), '--root', str(self.root), 'query', '--page', 'about'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        for value in ('0', '-1', 'bad'):
            self.assertNotEqual(self.cli('query', '--page', 'about', '--max-items', value).returncode, 0)

    def test_missing_map_and_duplicate_keys(self):
        self.assertEqual(self.cli('query', '--page', 'about').returncode, 2)
        self.write('acf-json/duplicate.json', (self.root / 'acf-json/group_about.json').read_text())
        result = self.cli('build')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Duplicate ACF', result.stderr)

    def test_html_only_reuse_is_inferred(self):
        result = self.result('query', '--file', 'UI/About.html')
        matches = [i for i in result['items'] if i['category'] == 'matching_component']
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['edge']['status'], 'inferred')

    def test_variable_or_namespaced_calls_not_wordpress_calls(self):
        self.write('variable.php', "<?php $get_field('about_history_list'); Other\\get_template_part('template-parts/shared/cta'); $x->get_field('about_goal_list');")
        self.assertFalse(any(e['source'] == 'variable.php' for e in self.graph()['edges']))


if __name__ == '__main__':
    unittest.main()
