import sys
import os
import argparse
import configparser
import io
import codecs

NB_VERSION = 4

def main(args=None):
    """The main routine."""
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser()
    parser.add_argument("action", help="create, check, run, make-nb, or run-nb")
    parser.add_argument("--directory", "-dir", default=os.getcwd(), 
                        help="path to directory with a .sciunit file")
    parser.add_argument("--stop", "-s", default=True, 
                        help="stop and raise errors, halting the program")
    args = parser.parse_args()
    #args.directory = os.getcwd() if args.directory is None else args.directory
    file_path = os.path.join(args.directory,'.sciunit')
    if args.action == 'create':
        create(file_path)
    elif args.action == 'check':
        config = parse(file_path, show=True)
        print("\nNo configuration errors reported.")
    elif args.action == 'run':
        config = parse(file_path)
        run(config, path=args.directory, stop_on_error=args.stop)
    elif args.action == 'make-nb':
        config = parse(file_path)
        make_nb(config, path=args.directory, stop_on_error=args.stop)
    elif args.action == 'run-nb':
        config = parse(file_path)
        run_nb(config, path=args.directory, stop_on_error=args.stop)
    else:
        raise NameError('No such action %s' % args.action)
    cleanup(config, path=args.directory)


def create(file_path):
    """Create a default .sciunit config file if one does not already exist"""
    if os.path.exists(file_path):
        raise IOError("There is already a configuration file at %s" % file_path)
    with open(file_path,'w') as f:
        config = configparser.ConfigParser()
        config.add_section('misc')
        config.set('misc', 'config-version', '1.0')
        config.add_section('root')
        config.set('root', 'path', '.')
        config.add_section('models')
        config.set('models', 'module', 'models')
        config.add_section('tests')
        config.set('tests', 'module', 'tests')
        config.add_section('suites')
        config.set('suites', 'module', 'suites')
        config.write(f)


def parse(file_path=None, show=False):
    """Parse a .sciunit config file"""
    if file_path is None:
        path = os.path.join(os.getcwd(),'.sciunit')
    if not os.path.exists(file_path):
        raise IOError('No .sciunit file was found at %s' % file_path)

    # Load the configuration file
    config = configparser.RawConfigParser(allow_no_value=True)
    config.read(file_path)

    # List all contents
    for section in config.sections():
        if show:
            print(section)
        for options in config.options(section):
            if show:
                print("\t%s: %s" % (options,config.get(section, options)))
    return config


def prep(config=None, path=None):
    if config is None:
        config = parse()
    if path is None:
        path = os.getcwd()
    root = config.get('root','path')
    root = os.path.join(path,root)
    if sys.path[0] != root:
        sys.path.insert(0,root)


def run(config, path=None, stop_on_error=True):
    """Run sciunit tests for the given configuration"""
    
    if path is None:
        path = os.getcwd()
    prep(config, path=path)

    models = __import__('models')
    tests = __import__('tests')
    suites = __import__('suites')

    for x in ['models','tests','suites']:
        module = __import__(x)
        assert hasattr(module,x), "'%s' module requires attribute '%s'" % (x,x)     

    for test in tests.tests:
        score_array = test.judge(models.models, stop_on_error=stop_on_error)
        print('\nTest %s:\n%s\n' % (test,score_array))

    for suite in suites.suites:
        score_matrix = suite.judge(models.models, stop_on_error=stop_on_error)
        print('\nSuite %s:\n%s\n' % (suite,score_matrix))


def make_nb(config, path=None, stop_on_error=True):
    """Create a Jupyter notebook sciunit tests for the given configuration"""

    from nbformat.v4.nbbase import new_notebook,new_markdown_cell
    import nbformat
    
    if path is None:
        path = os.getcwd()
    root = config.get('root','path')
    root = os.path.join(path,root)
    root = os.path.realpath(root)
    nb_name = config.get('misc','nb-name')
    mpl_style = config.get('misc','matplotlib',fallback='inline')
    
    cells = [new_markdown_cell('## Sciunit Testing Notebook for %s' % \
                               os.path.split(os.path.realpath(root))[1])]
    add_code_cell(cells, (
        "%%matplotlib %s\n"
        "from IPython.display import display\n"
        "import sys\n"
        "if sys.path[0] != '%s':\n"
        "  sys.path.insert(0,'%s')") % (mpl_style,root,root))
    add_code_cell(cells, (
        "import models, tests, suites"))
    add_code_cell(cells, (
        "for test in tests.tests:\n"
        "  score_array = test.judge(models.models, stop_on_error=%r)\n"
        "  display(score_array)") % stop_on_error)
    add_code_cell(cells, (
        "for suite in suites.suites:\n"
        "  score_matrix = suite.judge(models.models, stop_on_error=%r)\n"
        "  display(score_matrix)") % stop_on_error)

    nb = new_notebook(cells=cells,
        metadata={
            'language': 'python',
            })
        
    nb_path = os.path.join(root,'%s.ipynb' % nb_name)
    with codecs.open(nb_path, encoding='utf-8', mode='w') as nb_file:
        nbformat.write(nb, nb_file, NB_VERSION)
    print('Created Jupyter notebook at:\n%s' % nb_path)


def run_nb(config, path=None, stop_on_error=True):
    if path is None:
        path = os.getcwd()
    root = config.get('root','path')
    root = os.path.join(path,root)
    nb_name = config.get('misc','nb-name')
    nb_path = os.path.join(root,'%s.ipynb' % nb_name)
    if not os.path.exists(nb_path):
        print(("No notebook found at %s. "
               "Create the notebook first with make-nb?") % path)
        sys.exit(0)
    
    import nbformat
    from nbconvert.preprocessors import ExecutePreprocessor
    with codecs.open(nb_path, encoding='utf-8', mode='r') as nb_file:
        nb = nbformat.read(nb_file, as_version=NB_VERSION)
    ep = ExecutePreprocessor(timeout=600)#, kernel_name='python3')
    ep.preprocess(nb, {'metadata': {'path': root}})
    with codecs.open(nb_path, encoding='utf-8', mode='w') as nb_file:
        nbformat.write(nb, nb_file, NB_VERSION)


def add_code_cell(cells, source):
    from nbformat.v4.nbbase import new_code_cell
    n_code_cells = len([c for c in cells if c['cell_type']=='code'])
    cells.append(new_code_cell(source=source,execution_count=n_code_cells+1))


def cleanup(config=None, path=None):
    if config is None:
        config = parse()
    if path is None:
        path = os.getcwd()
    root = config.get('root','path')
    root = os.path.join(path,root)
    if sys.path[0] == root:
        sys.path.remove(root)


if __name__ == '__main__':
    main()
