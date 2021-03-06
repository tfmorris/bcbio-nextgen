"""Annotate structural variant calls with associated genes.
"""
from bcbio import utils
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline import datadict as dd
from bcbio.provenance import do

def add_genes(in_file, data, max_distance=10000):
    """Add gene annotations to a BED file from pre-prepared RNA-seq data.

    max_distance -- only keep annotations within this distance of event
    """
    import pybedtools
    gene_file = dd.get_gene_bed(data)
    if gene_file and utils.file_exists(in_file):
        out_file = "%s-annotated.bed" % utils.splitext_plus(in_file)[0]
        if not utils.file_uptodate(out_file, in_file):
            input_rec = iter(pybedtools.BedTool(in_file)).next()
            # keep everything after standard chrom/start/end, 1-based
            extra_fields = range(4, len(input_rec.fields) + 1)
            # keep the new gene annotation
            gene_index = len(input_rec.fields) + 4
            extra_fields.append(gene_index)
            columns = ",".join([str(x) for x in extra_fields])
            max_column = max(extra_fields) + 1
            ops = ",".join(["distinct"] * len(extra_fields))
            with file_transaction(data, out_file) as tx_out_file:
                # swap over gene name to '.' if beyond maximum distance
                # cut removes the last distance column which can cause issues
                # with bedtools merge: 'ERROR: illegal character '.' found in integer conversion of string'
                distance_filter = (r"""awk -F$'\t' -v OFS='\t' '{if ($NF > %s) $%s = "."} {print}'""" %
                                   (max_distance, gene_index))
                cmd = ("sort -k1,1 -k2,2n {in_file} | "
                       "bedtools closest -d -t all -a - -b {gene_file} | "
                       "{distance_filter} | cut -f 1-{max_column} | "
                       "bedtools merge -i - -c {columns} -o {ops} -delim ';' > {tx_out_file}")
                do.run(cmd.format(**locals()), "Annotate BED file with gene info")
        return out_file
    else:
        return in_file
