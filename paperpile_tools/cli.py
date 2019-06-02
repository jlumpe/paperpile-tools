import os
import json

import click

from . import bibliography as bib
from .util import find_pp_bibtex, Bijection, get_bijection



@click.group()
def cli():
	pass


def resolve_conflicts_interactively(keymap, updates, conflicts):
	pass


def resolve_conflicts_automatically(keymap, updates, conflicts):
	pass


def print_autoassign_summary(updates, conflicts):

	if updates:
		click.echo('Assigned %d keys:' % len(updates))
		for old_key in sorted(updates.left):
			click.echo('%-30s --> %s' % (old_key, updates.ltr[old_key]))
	else:
		click.echo('No additional assignments made.')

	click.echo()

	if conflicts:
		nskipped = sum(map(len, conflicts.values()))
		click.echo('Skipped %d keys due to %d conflicts:' % (nskipped, len(conflicts)))
		for reduced in sorted(conflicts.keys()):
			click.echo(reduced)
			for key in conflicts[reduced]:
				click.echo('\t' + key)


@cli.command()
@click.option('-o', '--output', type=click.File('w'),
                 help='Where to write modified bibtex file to')
@click.option('-k', '--keymap', 'keymap_file', type=click.File('r'),
                 help='Existing keymap file to use')
@click.option('-a', '--auto-assign', is_flag=True,
                 help='Auto-assign keys')
@click.option('-i', '--interactive', is_flag=True,
                 help='Resolve auto-assignment conflicts interactively')
@click.option('-r', '--resolve-conflicts', 'auto_resolve', is_flag=True,
              help='Resolve auto-assignment conflicts automatically')
@click.option('-s', '--summary', is_flag=True,
              help='Print auto-assignment summary')
@click.option('-u', '--update', is_flag=True,
                 help='Update bibtex file in-place')
@click.option('-m', '--merge', 'merge_into', type=click.Path(exists=True, dir_okay=False, writable=True),
              help='Merge into existing bibtex file')
@click.option('-w', '--write-keymap', type=click.File('w'),
                 help='File to write updated keymap to')
@click.argument('bibfile', type=click.Path(exists=True))
def assignkeys(bibfile, output, keymap_file, auto_assign, interactive, auto_resolve,
               summary, update, merge_into, write_keymap):
	"""Update IDs/keys of entries in exported .bib file.

	The IDs/keys of the entries are updated according to a keymap, which maps
	Paperpile keys to their replacements. This mapping may loaded from a JSON
	file using the --keymap option. You can also use the --auto-assign option
	which generates (or updates) the keymap to remove the annoying random
	2-character suffix Paperpile automatically adds.

	BIBFILE should be the path to the exported .bib file, or the directory
	to search for the file in. If multiple export files are found, the most
	recently created one is used.
	"""
	# if keymap_file is None and not auto_assign:
		# raise click.ClickException('Must specify either --keymap or --auto-assign option')
	if sum([output is not None, update, merge_into is not None]) > 1:
		raise click.ClickException('The --output, --update, and --merge options are mutually exclusive')
	if interactive and auto_resolve:
		raise click.ClickException('The --interactive and --resolve-conflicts options are mutually exlusive')

	# Locate most recent if given directory
	if os.path.isdir(bibfile):
		directory = bibfile
		bibfile = find_pp_bibtex(directory)
		if bibfile is None:
			raise click.ClickException('No Paperpile bibtex files found in %s' % directory)
		click.echo('Using most recent Paperpile export in directory: %s' % bibfile, err=True)

	# Read source bibliography
	with open(bibfile) as f:
		db = bib.read_bibliography(f, check=True)

	# Merging into existing?
	if merge_into is not None:
		with open(merge_into) as f:
			target_db = bib.read_bibliography(f, check=True)
		keymap = bib.keymap_from_bibliography(target_db)
		db = bib.merge_dbs(bib.revert_keys(target_db), db)

	else:
		keymap = Bijection()

	# Read keymap file
	if keymap_file is not None:
		file_keymap = Bijection.from_ltr(json.load(keymap_file))
		keymap.update_left(file_keymap)

	# Auto-assign
	if auto_assign:
		updates, conflicts = bib.assign_reduced_keys(db.entries_dict, keymap=keymap)

		if conflicts and interactive:
			resolve_conflicts_interactively(keymap, updates, conflicts)

		if summary:
			print_autoassign_summary(updates, conflicts)

		keymap |= updates

	else:
		conflicts = {}

	dbout = bib.update_keys(db, keymap)
	if conflicts:
		dbout.comments = [bib.make_key_sub_comment(keymap, [oldkey for newkey in sorted(conflicts) for oldkey in conflicts[newkey]])]

	# Write bibliography
	if output is not None:
		bib.write_bibliography(output, dbout)

	# Update original bibliography file
	if update:
		with open(bibfile, 'w') as f:
			bib.write_bibliography(f, dbout)

	# Merge into existing
	if merge_into is not None:
		with open(merge_into, 'w') as f:
			bib.write_bibliography(f, dbout)

	# Write keymap
	if write_keymap is not None:
		json.dump(dict(keymap), write_keymap, indent='\t', sort_keys=True)

