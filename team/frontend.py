"""Defines the web routes of the website.

For actual content generation see the content.py module.
"""
from flask import Blueprint, render_template, jsonify, request, redirect, current_app, flash
from flask_nav.elements import Navbar, Link, View, Text
from flask_login import (current_user, login_required, login_user,
                         logout_user)
from .content import get_cluster_plot, search_gene_names, \
    get_mch_scatter, get_mch_box, get_mch_box_two_species, \
    find_orthologs, FailToGraphException, get_corr_genes, \
    gene_id_to_name, randomize_cluster_colors, get_mch_heatmap
from . import nav
from . import cache
from os import walk
from .forms import LoginForm
from .user import User

import dominate
from dominate.tags import img

# get images here
lockimage = img(src='static/img/lock.png', height='20', width='20')
unlockimage = img(src='static/img/unlock.png', height='20', width='20')
separator = img(src='static/img/separate.png', height='25', width='10')

frontend = Blueprint('frontend', __name__) # Flask "bootstrap"

# Find all the samples in the data directory
dir_list = next(walk(current_app.config['DATA_DIR']))[1]

dir_list_links = []

first = True

for x in dir_list:
	if not first:
		dir_list_links.append(Text(separator))
	dir_list_links.append(Link(x, x))
	# if x is private, add lockimage
	dir_list_links.append(Text(lockimage))
	# if x is public, add unlockimage
	dir_list_links.append(Text(unlockimage))
	first = False

nav.register_element('frontend_top',
                     Navbar('',*dir_list_links))

# Visitor routes
@frontend.route('/')
def index():
    # Index is not needed since this site is embedded as a frame
    # We use JS redirect b/c reverse proxy will be confused about subdirectories
    html = \
    """To be redirected manually, click <a href="./hsa">here</a>.
    <script>
        window.location = "./hsa"; 
        window.location.replace("./hsa");
    </script>
    """
    return html
    
    # TODO: May need to switch to code below 
    #    depending on how to deal w/ published data

    # return \
    # """
    # To be redirected manually, click <a href="./human_combined">here</a>.' + \
    # <script>
    #      window.location = "./human_combined"; 
    #      window.location.replace("./human_combined");
    # </script>
    # """

@frontend.route('/<species>')
def species(species):
    return render_template('speciesview.html', species=species)

@frontend.route('/standalone/<species>/<gene>')
def standalone(species, gene):  # View gene body mCH plots alone
    return render_template('mch_standalone.html', species=species, gene=gene)


@frontend.route('/compare/<mmu_gid>/<hsa_gid>')
def compare(mmu_gid, hsa_gid):
    return render_template('compareview.html', mmu_gid=mmu_gid, hsa_gid=hsa_gid)


@frontend.route('/box_combined/<mmu_gid>/<hsa_gid>')
def box_combined(mmu_gid, hsa_gid):
    return render_template(
        'combined_box_standalone.html', mmu_gid=mmu_gid, hsa_gid=hsa_gid)


# API routes
@cache.cached(timeout=3600)
@frontend.route('/plot/cluster/<species>/<grouping>')
def plot_cluster(species, grouping):
    try:
        return jsonify(get_cluster_plot(species, grouping))
    except FailToGraphException:
        return 'Failed to produce cluster plot. Contact maintainer.'

@cache.cached(timeout=3600)
@frontend.route('/plot/mch/<species>/<gene>/<level>/<ptile_start>/<ptile_end>')
def plot_mch_scatter(species, gene, level, ptile_start, ptile_end):
    try:
        return get_mch_scatter(species, gene, level,
                               float(ptile_start), float(ptile_end))
    except (FailToGraphException, ValueError) as e:
        print(e)
        return 'Failed to produce mCH levels scatter plot. Contact maintainer.'


@cache.cached(timeout=3600)
@frontend.route('/plot/box/<species>/<gene>/<level>/<outliers_toggle>')
def plot_mch_box(species, gene, level, outliers_toggle):
    if outliers_toggle == 'outliers':
        outliers = True
    else:
        outliers = False

    try:
        return get_mch_box(species, gene, level, outliers)
    except (FailToGraphException, ValueError) as e:
        print(e)
        return 'Failed to produce mCH levels box plot. Contact maintainer.'


@cache.cached(timeout=3600)
@frontend.route(
    '/plot/box_combined/<species>/<gene_mmu>/<gene_hsa>/<level>/<outliers_toggle>')
def plot_mch_box_two_species(species, gene_mmu, gene_hsa, level, outliers_toggle):
    if outliers_toggle == 'outliers':
        outliers = True
    else:
        outliers = False

    try:
        return get_mch_box_two_species(species, gene_mmu, gene_hsa, level, outliers)
    except (FailToGraphException, ValueError) as e:
        print(e)
        return 'Failed to produce mCH levels box plot. Contact maintainer.'


@cache.cached(timeout=3600)
@frontend.route('/gene/names/<species>')
def search_gene_by_name(species):
    query = request.args.get('q', 'MustHaveAQueryString')
    return jsonify(search_gene_names(species, query))


@cache.cached(timeout=3600)
@frontend.route('/gene/id/<species>')
def search_gene_by_id(species):
    query = request.args.get('q', 'MustHaveAQueryString')
    return jsonify(gene_id_to_name(species, query))


@frontend.route('/gene/orthologs/<species>/<geneID>')
def orthologs(species, geneID):
    geneID = geneID.split('.')[0]
    if species == 'mmu':
        return jsonify(find_orthologs(mmu_gid=geneID))
    else:
        return jsonify(find_orthologs(hsa_gid=geneID))
    

@frontend.route('/gene/corr/<species>/<geneID>')
def correlated_genes(species, geneID):
    return jsonify(get_corr_genes(species,geneID))


@frontend.route('/plot/randomize_colors')
def randomize_colors():
    return jsonify(randomize_cluster_colors())


@frontend.route('/plot/heat/<species>/<level>/<ptile_start>/<ptile_end>')
def plot_mch_heatmap(species, level, ptile_start, ptile_end):
    query = request.args.get('q', 'MustHaveAQueryString')
    return get_mch_heatmap(species, level, ptile_start, ptile_end, query)

@frontend.route('/tabular/ensemble')
def tabular_screen():
    return render_template('tabular_ensemble.html')

@frontend.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.password_hash is not None and \
                user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            return redirect('/')
        else:
            flash('Invalid email or password.', 'form-error')
    return render_template('account/login.html', form=form)

# somewhere to logout
@frontend.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect('/')
