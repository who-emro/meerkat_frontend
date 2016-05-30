"""
meerkat_frontend.py

Root Flask app for the Meerkat Frontend.

This module runs as the root Flask app and mounts component Flask apps for
different services such as the API and Reports.
"""
import json, os
from slugify import slugify
from flask import Flask, send_file, render_template, request, current_app, abort, flash, g, redirect, url_for
import jinja2
from flask.ext.babel import Babel, gettext, ngettext, get_translations, get_locale, support
from .views.homepage import homepage
from .views.technical import technical
from .views.reports import reports
from .views.messaging import messaging
from .views.download import download
from .views.explore import explore
from . import common as c

# Create the Flask app
app = Flask(__name__)
babel = Babel(app)
app.jinja_options['extensions'].append('jinja2.ext.do')
app.config.from_object('config.Development')
app.config.from_envvar('MEERKAT_FRONTEND_SETTINGS')
app.config.from_envvar('MEERKAT_FRONTEND_API_SETTINGS', silent=True)
app.secret_key = 'some_secret'

if app.config.get( 'TEMPLATE_FOLDER', None ):
    my_loader = jinja2.ChoiceLoader([
        app.jinja_loader,
        jinja2.FileSystemLoader(app.config["TEMPLATE_FOLDER"]),
    ])
    app.jinja_loader = my_loader

# Set up the config files.
for k,v in app.config['COMPONENT_CONFIGS'].items():
    path = os.path.dirname(os.path.realpath(__file__)) + "/../" + v
    config = json.loads( open(path).read() ) 
    app.config[k] = {**app.config['SHARED_CONFIG'], **config}           

# Internationalisation

@babel.localeselector
def get_locale():
#    app.logger.info(g.get("language", app.config["DEFAULT_LANGUAGE"]))
    return g.get("language", 'en')


@app.route("/<language>/language_test")
def language_test(language):
    g.language = language
    return gettext("Hello, World!")


@messaging.url_value_preprocessor
@reports.url_value_preprocessor
@download.url_value_preprocessor
@explore.url_value_preprocessor
@technical.url_value_preprocessor
@homepage.url_value_preprocessor
def pull_lang_code(endpoint, values):
    app.logger.info("__init__")
    language = values.pop('language')
    if language not in app.config["SUPPORTED_LANGUAGES"]:
        abort(404, "Language not supported")
    g.language = language


@messaging.url_defaults
@reports.url_defaults
@download.url_defaults
@explore.url_defaults
@homepage.url_defaults
@technical.url_defaults
def add_language_code(endpoint, values):
    values.setdefault('language', app.config["DEFAULT_LANGUAGE"])


# Register the Blueprint modules
app.register_blueprint(homepage, url_prefix='/<language>')
app.register_blueprint(technical, url_prefix='/<language>/technical')
app.register_blueprint(reports, url_prefix='/<language>/reports')
app.register_blueprint(messaging, url_prefix='/<language>/messaging')
app.register_blueprint(download, url_prefix='/<language>/download')
app.register_blueprint(explore, url_prefix='/<language>/explore')


@app.route("/")
def root():
    return redirect("/" + app.config["DEFAULT_LANGUAGE"])


# Paths specified in config file
def prepare_function(template, config, authentication=False):
    def function():
        if authentication:
            auth = request.authorization
            if not auth or not c.check_auth(auth.username, auth.password):
                return c.authenticate()
        return render_template(template, content=config, week=c.api('/epi_week'))
    return function

# Add any extra country specific pages.
if "EXTRA_PAGES" in app.config:
  for url, value in app.config["EXTRA_PAGES"].items():
      path = os.path.dirname(os.path.realpath(__file__))+"/../"+value['config']
      if "authenticate" in value and value["authenticate"]:
          authenticate = True
      else:
          authenticate = False
      function = prepare_function(value['template'],
                                  json.loads( open(path).read()),
                                  authentication=authenticate)
      app.add_url_rule('/{}'.format(url), url, function)

@app.template_filter('slugify')
def slug(s):
    """Creates a slugify filter for Jinja templates"""
    return slugify(s)

# ERROR HANDLING
@app.route('/error/<int:error>/')
def error_test(error):
    """Serves requested error page for testing, by calling the ```abort()``` function.

       Args:
           error (int): The error code for the requested error.
    """
    abort(error)

@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(410)
@app.errorhandler(418)
@app.errorhandler(500)
@app.errorhandler(501)
@app.errorhandler(502)
def error500(error):
    """Serves page for generic error.
    
       Args:
           error (int): The error code given by the error handler.
    """
    flash("Sorry, something appears to have gone wrong.", "error")
    return render_template('error.html', error=error, content=current_app.config['TECHNICAL_CONFIG']), error.code

# Main
if __name__ == "__main__":
    app.run(host="localhost", port="8080", debug=True, reloader=True)
