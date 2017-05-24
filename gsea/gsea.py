from numpy import abs, asarray, empty, in1d, trapz, where
from numpy.random import shuffle
from pandas import DataFrame

from .dataplay.dataplay.a2d import normalize
from .file.file.file import establish_path
from .file.file.gct import write_gct


def single_sample_gsea(gene_x_sample,
                       gene_sets,
                       normalization='rank',
                       post_normalization_scale=1,
                       power=1,
                       statistic='Cumulative Area',
                       n_permutations=0,
                       file_path=None):
    """
    Gene-x-Sample ==> Gene-Set-x-Sample.
    :param gene_x_sample: DataFrame; (n_genes, n_samples)
    :param gene_sets: DataFrame;
    :param normalization: None | 'rank'
    :param power: number; power to raise gene_scores
    :param statistic: str; 'Cumulative Area' | 'Kolmogorov-Smirnov'
    :param n_permutations: int;
    :param file_path: str;
    :return: DataFrame; (n_gene_sets, n_samples)
    """

    # Rank normalize columns
    if normalization:
        g_x_s = normalize(gene_x_sample, 'rank', axis=0)
    else:
        g_x_s = gene_x_sample.copy()

    # TODO: Remove
    g_x_s *= post_normalization_scale

    # Make Gene-Set-x-Sample place holder
    gs_x_s = DataFrame(
        index=gene_sets.index, columns=g_x_s.columns, dtype=float)

    # For each gene set
    for gs_i, gs in gene_sets.iterrows():
        print('Computing {} enrichment ...'.format(gs_i))

        gs.dropna(inplace=True)

        # For each sample
        for s_i, s in g_x_s.items():

            # Compute enrichment score (ES)
            es = compute_enrichment_score(
                s, gs, power=power, statistic=statistic)

            if 0 < n_permutations:  # Score is permutation-normalized ES

                # ESs computed with permuted sample gene scores
                ess = empty(n_permutations)

                for i in range(n_permutations):
                    # Permute
                    shuffle(s)
                    # Compute ES
                    ess[i] = compute_enrichment_score(
                        s,
                        gs,
                        sort_gene_scores=False,
                        power=power,
                        statistic=statistic)

                # Compute permutation-normalized enrichment score
                gs_x_s.ix[gs_i, s_i] = es / ess.mean()

            else:  # Score is ES
                gs_x_s.ix[gs_i, s_i] = es

    if file_path:
        establish_path(file_path)
        write_gct(gs_x_s, file_path)

    return gs_x_s


def compute_enrichment_score(gene_scores,
                             gene_set_genes,
                             sort_gene_scores=True,
                             power=1,
                             statistic='Kolmogorov-Smirnov'):
    """
    Compute how much gene_scores enriches gene_set_genes.
    :param gene_scores: Series; (n_genes_with_score); sorted and gene indexed
    :param gene_set_genes: iterable; (n_genes)
    :param sort_gene_scores: bool; whether to sort gene_scores
    :param power: number; power to raise gene_scores
    :param statistic: str; 'Kolmogorov-Smirnov' | 'Cumulative Area'
    :return: float; enrichment score
    """

    if sort_gene_scores:  # Sort gene_scores
        gss = gene_scores.sort_values(ascending=False)
    else:
        gss = gene_scores.copy()

    # Check if gene_scores genes are in gene_set_genes
    in_ = in1d(gss.index, gene_set_genes, assume_unique=True)
    in_int = in_.astype(int)

    gss = abs(asarray(gss))**power

    hit = (gss * in_int) / gss[in_].sum()
    miss = (1 - in_int) / (in_.size - in_.sum())
    y = hit - miss

    # Compute enrichment score
    cs = y.cumsum()

    if statistic == 'Kolmogorov-Smirnov':

        max_es = cs.max()
        min_es = cs.min()

        es = where(abs(min_es) < abs(max_es), max_es, min_es)

    elif statistic == 'Cumulative Area':
        es = trapz(cs)

    else:
        raise ValueError('Unknown statistic: {}.'.format(statistic))

    # # TODO: Plot
    # import matplotlib as mpl
    # mpl.pyplot.figure(figsize=(8, 5))
    # ax = mpl.pyplot.gca()
    # ax.plot(range(in_.size), in_, color='black', alpha=0.16)
    # ax.plot(range(in_.size), y)
    # ax.plot(range(in_.size), cs)
    # mpl.pyplot.show()

    return es
